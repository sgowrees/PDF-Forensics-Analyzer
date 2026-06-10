import pytest
from django.urls import reverse
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestUserAdmin:
    def test_admin_list(self, client):
        admin = UserFactory(is_staff=True, is_superuser=True)
        client.force_login(admin)
        url = reverse("admin:users_user_changelist")
        response = client.get(url)
        assert response.status_code == 200

    def test_admin_detail(self, client):
        admin = UserFactory(is_staff=True, is_superuser=True)
        user = UserFactory()
        client.force_login(admin)
        url = reverse("admin:users_user_change", args=[user.pk])
        response = client.get(url)
        assert response.status_code == 200