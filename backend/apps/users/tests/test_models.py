import pytest
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = UserFactory()
        assert user.pk is not None
        assert user.email is not None

    def test_str(self):
        user = UserFactory(email="test@example.com")
        assert str(user) == "test@example.com"

    def test_email_is_username_field(self):
        from apps.users.models import User
        assert User.USERNAME_FIELD == "email"