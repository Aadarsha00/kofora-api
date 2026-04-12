from django.contrib import admin

from .models import Attribute, AttributeOption, ProductAttributeValue, VariantAttributeValue


class AttributeOptionInline(admin.TabularInline):
    model = AttributeOption
    extra = 0


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    inlines = [AttributeOptionInline]


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "attribute", "option")
    search_fields = ("product__name", "attribute__name", "option__value")


@admin.register(VariantAttributeValue)
class VariantAttributeValueAdmin(admin.ModelAdmin):
    list_display = ("id", "variant", "attribute", "option")
    search_fields = ("variant__sku", "attribute__name", "option__value")
