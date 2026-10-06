from django.contrib.auth import login, logout
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegistrationSerializer, LoginSerializer


from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        login(request, user)

        return Response(
            {
                "detail": "Successfully logged in.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)

        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


User = get_user_model()


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(email=email, is_active=True)

        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_url = (
                f"http://127.0.0.1:8000/api/auth/"
                f"password-reset/confirm/{uid}/{token}/"
            )

            send_mail(
                subject="Password reset",
                message=f"Use this link to reset your password:\n{reset_url}",
                from_email=None,
                recipient_list=[user.email],
            )

        return Response({"detail": "If an account with this email exists, a reset link has been sent."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        new_password = request.data.get("new_password")

        if not new_password:
            return Response({"detail": "New password is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)