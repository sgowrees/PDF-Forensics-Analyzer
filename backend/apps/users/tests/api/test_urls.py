import pytest
from django.urls import reverse, resolve
from apps.users.api.views import MeView, UserDetailView


@pytest.mark.django_db
class TestUserUrls:
    def test_me_url(self):
        url = reverse("user-me")
        assert resolve(url).func.view_class == MeView

    def test_user_detail_url(self):
        url = reverse("user-detail", args=[1])
        assert resolve(url).func.view_class == UserDetailView