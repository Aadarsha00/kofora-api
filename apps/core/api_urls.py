from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.authentication.urls")),
    path("users/", include("apps.users.urls")),
    path("addresses/", include("apps.addresses.urls")),
    path("categories/", include("apps.categories.urls")),
    path("products/", include("apps.products.urls")),
    path("attributes/", include("apps.attributes.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("cart/", include("apps.cart.urls")),
    path("orders/", include("apps.orders.urls")),
    path("payments/", include("apps.payments.urls")),
    path("subscriptions/", include("apps.subscriptions.urls")),
    path("discounts/", include("apps.discounts.urls")),
    path("shipping/", include("apps.shipping.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("search/", include("apps.search.urls")),
    path("contact/", include("apps.contact.urls")),
]
