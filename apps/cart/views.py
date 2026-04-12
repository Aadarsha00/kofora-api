from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.responses import api_success

from .models import Cart
from .serializers import CartSerializer


class MyCartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return api_success("Cart fetched successfully", serializer.data)
