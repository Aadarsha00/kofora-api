from django.db.models import Avg, Count, Q
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.responses import api_success
from apps.products.models import Product


class ProductSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Product.objects.filter(is_active=True, is_published=True)

        q = request.query_params.get("q", "").strip()
        category = request.query_params.get("category")
        size = request.query_params.get("size")
        color = request.query_params.get("color")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")

        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(short_description__icontains=q) | Q(full_description__icontains=q))
        if category:
            queryset = queryset.filter(categories__slug=category)
        if size:
            queryset = queryset.filter(variants__size=size)
        if color:
            queryset = queryset.filter(variants__color=color)
        if min_price:
            queryset = queryset.filter(variants__price__gte=min_price)
        if max_price:
            queryset = queryset.filter(variants__price__lte=max_price)

        ordering = request.query_params.get("ordering", "newest")
        if ordering == "price":
            queryset = queryset.order_by("variants__price")
        elif ordering == "popularity":
            queryset = queryset.annotate(popularity=Count("reviews")).order_by("-popularity")
        elif ordering == "rating":
            queryset = queryset.annotate(avg_rating=Avg("reviews__rating")).order_by("-avg_rating")
        else:
            queryset = queryset.order_by("-created_at")

        data = [
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "brand": product.brand,
            }
            for product in queryset.distinct()[:50]
        ]
        return api_success("Products fetched successfully", {"count": len(data), "results": data})
