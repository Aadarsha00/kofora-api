# Kofora Postman Pack

## Files

- Kofora_API.postman_collection.json
- Kofora_Local.postman_environment.json

## Import Order

1. Import Kofora_Local.postman_environment.json
2. Import Kofora_API.postman_collection.json
3. Select environment: Kofora Local

## Automation Included

- Collection-level Bearer auth with {{access_token}}
- Collection pre-request script auto-refreshes access token when token_expiry_epoch is near expiration
- Login test script auto-saves access_token and refresh_token
- Create Order test script auto-saves order_id

## Endpoint Groups and Input Mapping

## 01 Auth and Role Sessions

- POST /api/v1/auth/register/
  Required: email, username, password
  Optional: first_name, last_name, phone
- POST /api/v1/auth/login/
  Required: email, password
  Optional: none
- POST /api/v1/auth/token/refresh/
  Required: refresh
  Optional: none
- POST /api/v1/auth/logout/
  Required: refresh
  Optional: none
- POST /api/v1/auth/otp/send/
  Required: email
  Optional: none
- POST /api/v1/auth/otp/verify/
  Required: email, code
  Optional: none
- POST /api/v1/auth/forgot-password/
  Required: email
  Optional: none
- POST /api/v1/auth/reset-password/
  Required: token, new_password
  Optional: none
- POST /api/v1/auth/google/login/
  Required: code
  Optional: none

## 02 User Profile

- GET /api/v1/users/me/
  Required: Authorization
  Optional: none

## 03 Addresses

- GET /api/v1/addresses/
- POST /api/v1/addresses/
  Required: full_name, phone, country, state_province, city, postal_code, address_line_1
  Optional: company, address_line_2, address_type, is_default_shipping, is_default_billing, is_active
- GET /api/v1/addresses/{id}/
- PATCH /api/v1/addresses/{id}/
  Optional patchable fields: full_name, phone, company, country, state_province, city, postal_code, address_line_1, address_line_2, address_type, is_default_shipping, is_default_billing, is_active
- DELETE /api/v1/addresses/{id}/

## 04 Categories, Products, Bundles

- GET /api/v1/categories/
  Query options: is_active, parent, search, ordering
- POST /api/v1/categories/
  Required: name, slug
  Optional: description, parent, is_active, sort_order, seo_title, seo_description

- GET /api/v1/products/
  Query options: is_active, is_featured, is_published, base_currency, categories, search, ordering
- POST /api/v1/products/
  Required: name, slug
  Optional: brand, short_description, full_description, is_active, is_featured, base_currency, is_published, seo_title, seo_description, categories
- GET /api/v1/products/{id}/

- POST /api/v1/products/images/upload/
  Mode A (multipart): product, image(file), optional alt_text, sort_order, is_active
  Mode B (raw JSON): product, image_url, optional alt_text, sort_order, is_active

- GET /api/v1/products/bundles/
- POST /api/v1/products/bundles/
  Required: product, name, slug, bundle_price
  Optional: compare_at_price, is_active

## 05 Attributes and Inventory

- GET /api/v1/attributes/
  Query options: is_active, search
- POST /api/v1/attributes/
  Required: code, name
  Optional: is_active

- GET /api/v1/inventory/adjustments/
  Query options: reason, variant

## 06 Cart and Orders

- GET /api/v1/cart/me/
- POST /api/v1/orders/create-from-cart/
  Required: none
  Optional: customer_notes

## 07 Payments

- GET /api/v1/payments/transactions/
- POST /api/v1/payments/stripe/intents/
  Required: order_id, idempotency_key
- POST /api/v1/payments/paypal/orders/
  Required: order_id, idempotency_key, return_url, cancel_url
- POST /api/v1/payments/paypal/capture/
  Required: order_id, provider_payment_id
- POST /api/v1/payments/refunds/
  Required: payment_transaction_id, amount, reason
  Optional: idempotency_key
- POST /api/v1/payments/webhooks/stripe/
  Headers: Stripe-Signature
- POST /api/v1/payments/webhooks/paypal/
  Headers: PayPal-Transmission-Sig

## 08 Discounts

- GET /api/v1/discounts/
  Query options: is_active, discount_type, is_auto_applied
- POST /api/v1/discounts/
  Required: name, discount_type
  Optional: flat_amount, percentage, usage_limit, per_user_limit, starts_at, expires_at, minimum_order_amount, first_order_only, is_auto_applied, is_stackable, is_active

- GET /api/v1/discounts/coupons/
  Query options: is_active
- POST /api/v1/discounts/coupons/
  Required: discount, code
  Optional: is_active

- POST /api/v1/discounts/coupons/validate/
  Required: code, subtotal
  Optional: none

## 09 Shipping, Subscriptions, Reviews, Analytics, Search

- GET /api/v1/shipping/zones/
- POST /api/v1/shipping/zones/
  Required: name, country_code
  Optional: state_code, is_active

- GET /api/v1/shipping/methods/
- POST /api/v1/shipping/methods/
  Required: zone, name, code, base_rate
  Optional: free_shipping_threshold, is_active

- GET /api/v1/subscriptions/plans/
- GET /api/v1/subscriptions/mine/

- GET /api/v1/reviews/
  Query options: product, is_verified_purchase, moderation_status, is_published, rating
- POST /api/v1/reviews/
  Required: product, rating, body
  Optional: title

- POST /api/v1/reviews/images/upload/
  Mode A (multipart): review, image(file), optional alt_text
  Mode B (raw JSON): review, image_url, optional alt_text

- GET /api/v1/analytics/revenue-summary/

- GET /api/v1/search/products/
  Query options:
  q, category, size, color, min_price, max_price, ordering
  Supported ordering: newest, price, popularity, rating

## 10 Role Quick Runs

- Customer Quick Run
- Staff Quick Run
- Admin Quick Run

These role folders provide practical smoke-flow requests after each role login.
