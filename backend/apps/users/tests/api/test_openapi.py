import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestOpenAPI:
    def test_schema_accessible(self, client):
        user = __import__("apps.users.tests.factories", fromlist=["UserFactory"]).UserFactory
        admin = user(is_staff=True, is_superuser=True)
        client.force_login(admin)