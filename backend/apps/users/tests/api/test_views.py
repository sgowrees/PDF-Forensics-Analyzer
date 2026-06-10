import pytest
from django.urls import reverse
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestMeView:
    def test_get_me_authenticated(self, client):
        user = UserFactory()
        client.force_login(user)
        url = reverse("user-me")
        response = client.get(url)
        assert response.status_code == 200
        assert response.data["email"] == user.email

    def test_get_me_unauthenticated(self, client):
        url = reverse("user-me")
        response = client.get(url)
        assert response.status_code == 403

    def test_update_me(self, client):
        user = UserFactory()
        client.force_login(user)
        url = reverse("user-me")
        response = client.patch(url, {"first_name": "John"}, content_type="application/json")
        assert response.status_code == 200
        assert response.data["first_name"] == "John"