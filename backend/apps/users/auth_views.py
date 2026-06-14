from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(request, email=email, password=password)

        if not user:
            return Response({"error": "Invalid credentials"}, status=400)

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


class LogoutView(APIView):
    permission_classes = []

    def post(self, request):
        return Response({"message": "Logged out"})