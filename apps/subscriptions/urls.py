from rest_framework.routers import DefaultRouter

from .views import CustomerSubscriptionViewSet, SubscriptionPlanViewSet

router = DefaultRouter()
router.register("plans", SubscriptionPlanViewSet, basename="subscription-plan")
router.register("mine", CustomerSubscriptionViewSet, basename="customer-subscription")

urlpatterns = router.urls
