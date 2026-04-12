from rest_framework import viewsets

from .models import CustomerSubscription, SubscriptionPlan
from .serializers import CustomerSubscriptionSerializer, SubscriptionPlanSerializer


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer


class CustomerSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerSubscriptionSerializer

    def get_queryset(self):
        return CustomerSubscription.objects.filter(customer=self.request.user)
