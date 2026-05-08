from django.contrib import admin

from .models import Bundle, BundleItem, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "brand", "base_currency", "is_active", "is_featured", "is_published")
    list_filter = ("is_active", "is_featured", "is_published", "base_currency", "brand")
    search_fields = ("name", "slug", "brand")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("categories",)
    inlines = [ProductImageInline, ProductVariantInline]


class BundleItemInline(admin.TabularInline):
    model = BundleItem
    extra = 1


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "product", "bundle_price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "product__name")
    inlines = [BundleItemInline]
