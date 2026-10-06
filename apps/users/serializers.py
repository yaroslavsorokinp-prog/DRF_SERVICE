from django.contrib.auth import get_user_model
from rest_framework import serializers


User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        user = authenticate(
            username=attrs["username"],
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError("Invalid username or password.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        attrs["user"] = user
        return attrs