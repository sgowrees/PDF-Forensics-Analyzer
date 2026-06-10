import { useRef, useState, type DragEvent } from 'react'

interface FileUploadProps {
  onUpload: (file: File) => void
  loading: boolean
  disabled?: boolean
}

export function FileUpload({ onUpload, loading, disabled }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [selectedName, setSelectedName] = useState<string | null>(null)

  function pickFile(file: File | undefined) {
    if (!file || disabled || loading) return
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      return
    }
    setSelectedName(file.name)
    onUpload(file)
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragOver(false)
    pickFile(event.dataTransfer.files[0])
  }

  return (
    <div
      className={`upload-zone${dragOver ? ' drag-over' : ''}${loading ? ' loading' : ''}`}
      onDragOver={(event) => {
        event.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => !loading && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          inputRef.current?.click()
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(event) => pickFile(event.target.files?.[0])}
      />

      <div className="upload-icon" aria-hidden>
        PDF
      </div>

      {loading ? (
        <p className="upload-title">Analyzing document…</p>
      ) : (
        <>
          <p className="upload-title">Drop a PDF here or click to browse</p>
          <p className="upload-hint">Max 20 MB · Forensics run against trusted baselines</p>
        </>
      )}

      {selectedName && !loading && (
        <p className="upload-selected">Selected: {selectedName}</p>
      )}
    </div>
  )
}
