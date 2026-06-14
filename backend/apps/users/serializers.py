from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "date_joined", "is_active"]


class AdminUserRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        email = validated_data["email"]
        user = User(username=email, email=email)
        user.set_password(validated_data["password"])
        user.save()
        return user