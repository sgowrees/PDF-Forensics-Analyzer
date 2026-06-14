import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { login as apiLogin } from '../api/auth'
import { getMe, type User } from '../api/users'
import { clearTokens } from '../api/client'

type AuthContextType = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const me = await getMe()
    setUser(me)
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('access')
    if (!token) {
      setLoading(false)
      return
    }

    refreshUser()
      .catch(() => {
        clearTokens()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [refreshUser])

  const login = async (email: string, password: string) => {
    await apiLogin(email, password)
    const me = await getMe()
    setUser(me)
    return me
  }

  const logout = () => {
    clearTokens()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
