from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_success

from .serializers import UserSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return api_success("Profile fetched successfully", serializer.data)
