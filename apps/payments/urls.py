from django.urls import path

from .views import (
    PayPalCaptureOrderView,
    PayPalCreateOrderView,
    PayPalWebhookView,
    PaymentTransactionListView,
    StripeCreateCheckoutSessionView,
    StripeConfirmCheckoutSessionView,
    RefundCreateView,
    StripeCreateIntentView,
    StripeWebhookView,
)

urlpatterns = [
    path("transactions/", PaymentTransactionListView.as_view(), name="payments-transactions"),
    path("stripe/intents/", StripeCreateIntentView.as_view(), name="payments-stripe-intents"),
    path("stripe/checkout-sessions/", StripeCreateCheckoutSessionView.as_view(), name="payments-stripe-checkout-sessions"),
    path("stripe/checkout-sessions/confirm/", StripeConfirmCheckoutSessionView.as_view(), name="payments-stripe-checkout-sessions-confirm"),
    path("paypal/orders/", PayPalCreateOrderView.as_view(), name="payments-paypal-orders"),
    path("paypal/capture/", PayPalCaptureOrderView.as_view(), name="payments-paypal-capture"),
    path("refunds/", RefundCreateView.as_view(), name="payments-refunds"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="payments-webhook-stripe"),
    path("webhooks/paypal/", PayPalWebhookView.as_view(), name="payments-webhook-paypal"),
]
