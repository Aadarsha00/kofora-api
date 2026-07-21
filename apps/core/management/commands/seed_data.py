import base64
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.addresses.models import Address
from apps.analytics.models import CustomerEvent, DailyMetric, EventType
from apps.attributes.models import Attribute, AttributeOption, ProductAttributeValue, VariantAttributeValue
from apps.authentication.models import EmailOTP, GoogleOAuthAccount, PasswordResetToken
from apps.cart.models import Cart, CartBundleItem, CartVariantItem
from apps.catalog.models import ProductCollection
from apps.categories.models import Category
from apps.discounts.models import CouponCode, Discount, DiscountRule, DiscountUsage
from apps.inventory.models import InventoryAdjustment, LowStockAlert
from apps.notifications.models import NotificationLog, NotificationTemplate
from apps.orders.models import (
    Order,
    OrderAddressSnapshot,
    OrderItem,
    OrderStatusHistory,
    RefundRecord,
    ReturnRecord,
)
from apps.payments.models import PaymentTransaction, PaymentWebhookEvent, RefundTransaction
from apps.products.models import Bundle, BundleItem, Product, ProductImage, ProductVariant
from apps.reviews.models import Review, ReviewImage
from apps.search.models import SearchQueryLog
from apps.shipping.models import ShippingMethod, ShippingRateRule, ShippingZone
from apps.subscriptions.models import CustomerSubscription, SubscriptionEvent, SubscriptionPlan
from apps.users.models import UserProfile


class Command(BaseCommand):
    help = "Seed demo data for all project models"

    @staticmethod
    def _tiny_png(name: str) -> ContentFile:
        # 1x1 transparent PNG
        raw = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO8BfVUAAAAASUVORK5CYII="
        )
        return ContentFile(raw, name=name)

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        admin_user, _ = User.objects.get_or_create(
            email="admin@kofora.com",
            defaults={
                "username": "admin_kofora",
                "role": "admin",
                "is_email_verified": True,
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "last_name": "Kofora",
            },
        )
        admin_user.set_password("StrongPass123!")
        admin_user.save()

        staff_user, _ = User.objects.get_or_create(
            email="staff@kofora.com",
            defaults={
                "username": "staff_kofora",
                "role": "staff",
                "is_email_verified": True,
                "is_staff": True,
                "first_name": "Staff",
                "last_name": "Kofora",
            },
        )
        staff_user.set_password("StrongPass123!")
        staff_user.save()

        customer_user, _ = User.objects.get_or_create(
            email="customer@kofora.com",
            defaults={
                "username": "customer_kofora",
                "role": "customer",
                "is_email_verified": True,
                "first_name": "Customer",
                "last_name": "Kofora",
            },
        )
        customer_user.set_password("StrongPass123!")
        customer_user.save()

        UserProfile.objects.get_or_create(user=customer_user, defaults={"preferred_currency": "USD", "loyalty_points": 120})

        EmailOTP.objects.get_or_create(
            user=customer_user,
            email=customer_user.email,
            code="123456",
            defaults={"expires_at": timezone.now() + timedelta(minutes=10), "is_used": False},
        )
        PasswordResetToken.objects.get_or_create(
            user=customer_user,
            token="seed-reset-token-1",
            defaults={"expires_at": timezone.now() + timedelta(hours=1), "is_used": False},
        )
        GoogleOAuthAccount.objects.get_or_create(
            user=customer_user,
            defaults={"google_sub": "seed-google-sub-customer", "email": customer_user.email},
        )

        address, _ = Address.objects.get_or_create(
            user=customer_user,
            address_line_1="123 Market Street",
            postal_code="94105",
            defaults={
                "full_name": "Customer Kofora",
                "phone": "+15550000001",
                "country": "US",
                "state_province": "CA",
                "city": "San Francisco",
                "address_line_2": "Suite 500",
                "address_type": Address.ADDRESS_TYPE_HOME,
                "is_default_shipping": True,
                "is_default_billing": True,
                "is_active": True,
            },
        )

        parent_category, _ = Category.objects.get_or_create(
            slug="socks",
            defaults={
                "name": "Socks",
                "taxonomy_group": Category.TAXONOMY_PRODUCT_FAMILY,
                "description": "All socks",
                "is_active": True,
                "sort_order": 1,
                "seo_title": "Kofora Socks",
                "seo_description": "Premium socks",
                "created_by": admin_user,
                "updated_by": admin_user,
            },
        )
        category, _ = Category.objects.get_or_create(
            slug="calf",
            defaults={
                "parent": parent_category,
                "name": "Calf",
                "taxonomy_group": Category.TAXONOMY_HEIGHT,
                "description": "Calf height premium socks",
                "is_active": True,
                "sort_order": 2,
                "seo_title": "Calf Socks",
                "seo_description": "Calf height socks",
                "created_by": admin_user,
                "updated_by": admin_user,
            },
        )

        product, _ = Product.objects.get_or_create(
            slug="kofora-premium-crew",
            defaults={
                "name": "Kofora Premium Crew",
                "brand": "Kofora",
                "short_description": "Soft crew socks",
                "full_description": "Premium cotton blend crew socks for all-day comfort.",
                "is_active": True,
                "is_featured": True,
                "base_currency": Product.CURRENCY_USD,
                "is_published": True,
                "seo_title": "Kofora Premium Crew",
                "seo_description": "Premium crew socks",
                "created_by": admin_user,
                "updated_by": admin_user,
            },
        )
        product.categories.add(parent_category, category)

        if not ProductImage.objects.filter(product=product).exists():
            ProductImage.objects.create(
                product=product,
                image=self._tiny_png("seed-product.png"),
                alt_text="Seed product image",
                sort_order=1,
                is_active=True,
                created_by=admin_user,
                updated_by=admin_user,
            )

        variant, _ = ProductVariant.objects.get_or_create(
            sku="KOF-CRW-BLK-M",
            defaults={
                "product": product,
                "barcode": "123456789012",
                "title": "Black / M",
                "size": "M",
                "color": "Black",
                "price": Decimal("19.99"),
                "compare_at_price": Decimal("24.99"),
                "cost_price": Decimal("8.50"),
                "stock_quantity": 120,
                "reserved_quantity": 6,
                "low_stock_threshold": 12,
                "is_active": True,
                "weight_grams": 100,
                "created_by": admin_user,
                "updated_by": admin_user,
            },
        )

        bundle, _ = Bundle.objects.get_or_create(
            slug="crew-3-pack",
            defaults={
                "product": product,
                "name": "Crew 3 Pack",
                "bundle_price": Decimal("49.99"),
                "compare_at_price": Decimal("59.99"),
                "is_active": True,
                "created_by": admin_user,
                "updated_by": admin_user,
            },
        )
        BundleItem.objects.get_or_create(
            bundle=bundle,
            variant=variant,
            defaults={"quantity": 3, "created_by": admin_user, "updated_by": admin_user},
        )

        collection, _ = ProductCollection.objects.get_or_create(
            slug="spring-collection",
            defaults={
                "name": "Spring Collection",
                "description": "Spring featured socks",
                "is_active": True,
            },
        )
        collection.products.add(product)

        attribute, _ = Attribute.objects.get_or_create(
            code="material",
            defaults={"name": "Material", "is_active": True, "created_by": admin_user, "updated_by": admin_user},
        )
        option, _ = AttributeOption.objects.get_or_create(
            attribute=attribute,
            value="Cotton Blend",
            defaults={"sort_order": 1, "is_active": True, "created_by": admin_user, "updated_by": admin_user},
        )
        ProductAttributeValue.objects.get_or_create(
            product=product,
            attribute=attribute,
            option=option,
            defaults={"created_by": admin_user, "updated_by": admin_user},
        )
        VariantAttributeValue.objects.get_or_create(
            variant=variant,
            attribute=attribute,
            option=option,
            defaults={"created_by": admin_user, "updated_by": admin_user},
        )

        zone, _ = ShippingZone.objects.get_or_create(
            name="United States",
            country_code="US",
            defaults={"state_code": "", "is_active": True},
        )
        method, _ = ShippingMethod.objects.get_or_create(
            code="standard-us",
            defaults={
                "zone": zone,
                "name": "Standard Shipping",
                "base_rate": Decimal("6.99"),
                "free_shipping_threshold": Decimal("75.00"),
                "is_active": True,
            },
        )
        ShippingRateRule.objects.get_or_create(
            method=method,
            min_subtotal=Decimal("0.00"),
            defaults={"max_subtotal": Decimal("9999.99"), "rate": Decimal("6.99")},
        )

        plan, _ = SubscriptionPlan.objects.get_or_create(
            slug="monthly-3-pack",
            defaults={
                "name": "Monthly 3-Pack",
                "interval_unit": "month",
                "interval_count": 1,
                "price": Decimal("39.99"),
                "currency": "USD",
                "stripe_price_id": "price_seed_monthly_3pack",
                "is_active": True,
            },
        )

        discount, _ = Discount.objects.get_or_create(
            name="SAVE10",
            defaults={
                "discount_type": Discount.TYPE_PERCENT,
                "percentage": Decimal("10.00"),
                "minimum_order_amount": Decimal("50.00"),
                "is_active": True,
            },
        )
        coupon, _ = CouponCode.objects.get_or_create(
            code="SAVE10",
            defaults={"discount": discount, "is_active": True},
        )
        DiscountRule.objects.get_or_create(discount=discount, product=product, defaults={"bundle": bundle, "subscription_plan": plan})

        cart, _ = Cart.objects.get_or_create(
            user=customer_user,
            defaults={
                "currency": "USD",
                "shipping_address": address,
                "billing_address": address,
                "shipping_method": method,
                "applied_coupon": coupon,
                "is_abandoned": False,
            },
        )
        CartVariantItem.objects.get_or_create(cart=cart, variant=variant, defaults={"quantity": 2})
        CartBundleItem.objects.get_or_create(cart=cart, bundle=bundle, defaults={"quantity": 1})

        order, _ = Order.objects.get_or_create(
            order_number="KOF-SEED-0001",
            defaults={
                "customer": customer_user,
                "currency": "USD",
                "subtotal": Decimal("89.97"),
                "discount_amount": Decimal("8.99"),
                "shipping_amount": Decimal("6.99"),
                "tax_amount": Decimal("7.04"),
                "grand_total": Decimal("95.01"),
                "payment_status": "paid",
                "fulfillment_status": Order.STATUS_PROCESSING,
                "customer_notes": "Seed order",
                "staff_notes": "Created by seed command",
            },
        )
        OrderAddressSnapshot.objects.get_or_create(
            order=order,
            address_type=OrderAddressSnapshot.TYPE_SHIPPING,
            defaults={
                "full_name": address.full_name,
                "phone": address.phone,
                "company": address.company,
                "country": address.country,
                "state_province": address.state_province,
                "city": address.city,
                "postal_code": address.postal_code,
                "address_line_1": address.address_line_1,
                "address_line_2": address.address_line_2,
            },
        )
        OrderAddressSnapshot.objects.get_or_create(
            order=order,
            address_type=OrderAddressSnapshot.TYPE_BILLING,
            defaults={
                "full_name": address.full_name,
                "phone": address.phone,
                "company": address.company,
                "country": address.country,
                "state_province": address.state_province,
                "city": address.city,
                "postal_code": address.postal_code,
                "address_line_1": address.address_line_1,
                "address_line_2": address.address_line_2,
            },
        )
        OrderItem.objects.get_or_create(
            order=order,
            variant_sku=variant.sku,
            defaults={
                "product_name": product.name,
                "size": variant.size,
                "color": variant.color,
                "quantity": 2,
                "unit_price": variant.price,
                "discount_amount": Decimal("0.00"),
                "line_total": Decimal("39.98"),
            },
        )
        OrderStatusHistory.objects.get_or_create(
            order=order,
            to_status=Order.STATUS_PROCESSING,
            defaults={"from_status": Order.STATUS_PAID, "changed_by": staff_user, "note": "Seed lifecycle event"},
        )
        RefundRecord.objects.get_or_create(order=order, amount=Decimal("5.00"), defaults={"reason": "Seed partial refund", "status": "processed"})
        ReturnRecord.objects.get_or_create(order=order, reason="Seed size issue", defaults={"status": "requested"})

        payment_txn, _ = PaymentTransaction.objects.get_or_create(
            provider_payment_id="pi_seed_0001",
            defaults={
                "order": order,
                "provider": PaymentTransaction.PROVIDER_STRIPE,
                "amount": order.grand_total,
                "currency": order.currency,
                "status": PaymentTransaction.STATUS_SUCCEEDED,
                "idempotency_key": "seed-pi-1",
            },
        )
        RefundTransaction.objects.get_or_create(
            provider_refund_id="re_seed_0001",
            defaults={
                "payment_transaction": payment_txn,
                "amount": Decimal("5.00"),
                "status": "succeeded",
                "reason": "Seed refund",
            },
        )
        PaymentWebhookEvent.objects.get_or_create(
            event_id="evt_seed_0001",
            defaults={
                "provider": PaymentTransaction.PROVIDER_STRIPE,
                "event_type": "payment_intent.succeeded",
                "signature": "seed-signature",
                "is_verified": True,
                "processed_at": timezone.now(),
            },
        )

        customer_sub, _ = CustomerSubscription.objects.get_or_create(
            stripe_subscription_id="sub_seed_0001",
            defaults={
                "customer": customer_user,
                "plan": plan,
                "start_date": timezone.now().date(),
                "renewal_date": (timezone.now() + timedelta(days=30)).date(),
                "status": CustomerSubscription.STATUS_ACTIVE,
            },
        )
        SubscriptionEvent.objects.get_or_create(
            subscription=customer_sub,
            event_type="subscription_created",
            defaults={"source": "stripe", "note": "Seed subscription event"},
        )

        DiscountUsage.objects.get_or_create(
            discount=discount,
            user=customer_user,
            coupon_code=coupon,
            order_id=order.order_number,
        )

        review, _ = Review.objects.get_or_create(
            customer=customer_user,
            product=product,
            defaults={
                "rating": 5,
                "title": "Excellent",
                "body": "High quality and very comfortable.",
                "is_verified_purchase": True,
                "moderation_status": Review.MOD_APPROVED,
                "is_published": True,
            },
        )
        if not ReviewImage.objects.filter(review=review).exists():
            ReviewImage.objects.create(
                review=review,
                image=self._tiny_png("seed-review.png"),
                alt_text="Seed review image",
            )

        InventoryAdjustment.objects.get_or_create(
            variant=variant,
            quantity_delta=-2,
            reason=InventoryAdjustment.REASON_ORDER,
            reference=order.order_number,
            defaults={"notes": "Seed order reservation", "adjusted_by": staff_user},
        )
        LowStockAlert.objects.get_or_create(
            variant=variant,
            threshold=variant.low_stock_threshold,
            current_stock=variant.available_quantity,
            defaults={"is_resolved": False},
        )

        event_type, _ = EventType.objects.get_or_create(
            code="purchase_completed",
            defaults={"name": "Purchase Completed", "is_funnel_step": True},
        )
        CustomerEvent.objects.get_or_create(
            user=customer_user,
            event_type=event_type,
            product=product,
            variant=variant,
            session_id="seed-session-1",
            source="seed",
        )
        DailyMetric.objects.get_or_create(
            metric_date=timezone.now().date(),
            defaults={
                "total_revenue": Decimal("95.01"),
                "order_count": 1,
                "average_order_value": Decimal("95.01"),
                "repeat_customer_count": 1,
            },
        )

        NotificationTemplate.objects.get_or_create(
            code="welcome_email",
            defaults={
                "subject_template": "Welcome to Kofora",
                "body_template": "Hello {{ first_name }}, welcome to Kofora.",
                "is_active": True,
            },
        )
        NotificationLog.objects.get_or_create(
            user=customer_user,
            recipient=customer_user.email,
            subject="Seed Notification",
            defaults={"notification_type": NotificationLog.TYPE_EMAIL, "status": "sent", "error_message": ""},
        )

        SearchQueryLog.objects.get_or_create(
            user=customer_user,
            query="crew socks",
            defaults={
                "category_slug": category.slug,
                "size": variant.size,
                "color": variant.color,
                "min_price": Decimal("10.00"),
                "max_price": Decimal("100.00"),
            },
        )

        self.stdout.write(self.style.SUCCESS("Seed completed successfully for all project models."))
