from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import UserSerializer, RegisterSerializer, AdminUserRoleSerializer
from .premissions import IsAdmin

from apps.documents.models import Document, AnalysisResult, TemplateDocument


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = []


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == "admin":
            docs = Document.objects.all()
        else:
            docs = Document.objects.filter(owner=user)

        payload = {
            "total_documents": docs.count(),
            "status_breakdown": {
                "pending": docs.filter(status="pending").count(),
                "processing": docs.filter(status="processing").count(),
                "complete": docs.filter(status="complete").count(),
                "failed": docs.filter(status="failed").count(),
            },
            "risk_breakdown": {
                "LOW": AnalysisResult.objects.filter(document__in=docs, risk="LOW").count(),
                "MEDIUM": AnalysisResult.objects.filter(document__in=docs, risk="MEDIUM").count(),
                "HIGH": AnalysisResult.objects.filter(document__in=docs, risk="HIGH").count(),
            },
        }

        if user.role == "admin":
            payload["total_users"] = User.objects.count()
            payload["total_baselines"] = TemplateDocument.objects.count()

        return Response(payload)


class AdminUserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = User.objects.order_by("-date_joined")


class AdminUserRoleView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        serializer = AdminUserRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_object_or_404(User, pk=pk)
        new_role = serializer.validated_data["role"]

        if user.pk == request.user.pk and new_role != User.Role.ADMIN:
            return Response(
                {"detail": "You cannot remove your own admin access."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.role = new_role
        user.save(update_fields=["role"])

        return Response(UserSerializer(user).data)