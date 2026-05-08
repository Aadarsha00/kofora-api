from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_error, api_success

from .serializers import ChangePasswordSerializer, UserSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return api_success("Profile fetched successfully", serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_error("Invalid profile data", serializer.errors)
        serializer.save()
        return api_success("Profile updated successfully", serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return api_error("Invalid password data", serializer.errors)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password", "updated_at"])
        return api_success("Password changed successfully")
