from django.contrib import admin

from .models import Bundle, BundleItem, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    autocomplete_fields = ("variant",)
    fields = ("image", "variant", "alt_text", "sort_order", "is_active")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "variant":
            product_id = request.resolver_match.kwargs.get("object_id") if request.resolver_match else None
            if product_id:
                kwargs["queryset"] = ProductVariant.objects.filter(product_id=product_id).order_by("color", "size", "sku")
            else:
                kwargs["queryset"] = ProductVariant.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "sku",
        "title",
        "size",
        "color",
        "price",
        "compare_at_price",
        "stock_quantity",
        "reserved_quantity",
        "is_active",
        "image_override",
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "sku", "title", "color", "size", "price", "stock_quantity", "reserved_quantity", "is_active")
    list_filter = ("is_active", "product", "color", "size")
    search_fields = ("sku", "title", "color", "size", "product__name", "product__slug")
    autocomplete_fields = ("product",)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "variant", "alt_text", "sort_order", "is_active")
    list_filter = ("is_active", "product")
    search_fields = ("product__name", "product__slug", "variant__sku", "variant__title", "alt_text")
    autocomplete_fields = ("product", "variant")


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
