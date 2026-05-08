from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ReviewImageUploadView, ReviewViewSet

router = DefaultRouter()
router.register("", ReviewViewSet, basename="review")

urlpatterns = [
	path("images/upload/", ReviewImageUploadView.as_view(), name="reviews-image-upload"),
] + router.urls
