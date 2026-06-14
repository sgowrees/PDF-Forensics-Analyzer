from django.urls import path
from .views import (
    AdminUserListView,
    AdminUserRoleView,
    DashboardView,
    MeView,
    RegisterView,
)
from .auth_views import LoginView, LogoutView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("dashboard/", DashboardView.as_view()),
    path("admin/users/", AdminUserListView.as_view()),
    path("admin/users/<int:pk>/role/", AdminUserRoleView.as_view()),
]