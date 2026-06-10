from django.urls import path
from .views import MeView, UserDetailView

urlpatterns = [
    path("me/", MeView.as_view(), name="user-me"),
    path("<int:id>/", UserDetailView.as_view(), name="user-detail"),
]