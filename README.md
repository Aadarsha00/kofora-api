# Kofora Ecommerce Backend

Production-grade, API-first ecommerce backend for Kofora (premium sock brand), built with Django + DRF using normalized relational schema and modular service-oriented architecture.

## Tech Stack

- Django
- Django REST Framework
- SQLite (local development)
- PostgreSQL (production)
- Redis (cache + Celery broker/result backend)
- Celery + Celery Beat
- JWT (SimpleJWT)
- Google OAuth endpoint scaffold
- Email OTP verification flows
- Gunicorn + Nginx + systemd on Ubuntu VPS
- No Docker

## Core Principles Implemented

- No JSONField used in model layer
- Normalized relational schema for business data
- API v1 namespaced under `/api/v1/`
- Structured API envelope for success and error responses
- Service layer for business workflows (cart totals, order creation, inventory, discount application)
- Strong Django admin for internal operations

## Project Structure

- `kofora_backend/` Django project config and split settings
- `apps/core/` shared response envelope, pagination, base models, permissions
- `apps/users/` custom user and user profile
- `apps/authentication/` register/login/JWT/OTP/password reset/Google OAuth endpoint
- `apps/addresses/` saved customer addresses with shipping/billing defaults
- `apps/categories/` nested parent-child categories
- `apps/products/` products, media, variants, bundles
- `apps/attributes/` normalized product and variant attribute values
- `apps/inventory/` stock adjustments and low stock alerts
- `apps/cart/` authenticated cart with variant and bundle items
- `apps/orders/` order snapshots, status timeline, refunds/returns
- `apps/payments/` Stripe/PayPal-ready transactions + webhook tracking
- `apps/subscriptions/` plans and customer subscriptions
- `apps/discounts/` discount engine models and coupon codes
- `apps/shipping/` shipping zones, methods, and rules
- `apps/reviews/` verified reviews and image attachments
- `apps/analytics/` normalized event types and BI metrics
- `apps/notifications/` template + log + async email tasks
- `apps/search/` practical search/filter endpoint for VPS deployment

## Local Setup

1. Create virtual environment and activate it.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Create env file:
   - `cp .env.example .env`
4. Use development settings:
   - `set DJANGO_SETTINGS_MODULE=kofora_backend.settings.development`
5. Run migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
6. Create superuser:
   - `python manage.py createsuperuser`
7. Start development server:
   - `python manage.py runserver 127.0.0.1:8000`
   - The frontend `.env.local` points to `http://127.0.0.1:8000/api/v1` for local Kofora development.
8. Start Celery worker and beat in separate terminals:
   - `celery -A kofora_backend worker --loglevel=info`
   - `celery -A kofora_backend beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler`

## Order Stock Reservations

Unpaid orders reserve inventory while they are awaiting payment. Celery Beat runs `apps.orders.expire_unpaid_orders` every `ORDER_EXPIRATION_SWEEP_MINUTES` minutes and cancels unpaid orders older than `ORDER_PAYMENT_RESERVATION_MINUTES`, releasing their reserved stock.

Manual cleanup:

```bash
python manage.py expire_unpaid_orders --dry-run
python manage.py expire_unpaid_orders
```

## API Envelope

All API responses are wrapped by `apps.core.renderers.EnvelopedJSONRenderer`.

Success shape:

```json
{
  "success": true,
  "message": "Request successful",
  "data": {},
  "errors": null
}
```

Error shape:

```json
{
  "success": false,
  "message": "Request failed",
  "data": null,
  "errors": {}
}
```

## Key API Modules

- `/api/v1/auth/`
- `/api/v1/users/`
- `/api/v1/addresses/`
- `/api/v1/categories/`
- `/api/v1/products/`
- `/api/v1/attributes/`
- `/api/v1/inventory/`
- `/api/v1/cart/`
- `/api/v1/orders/`
- `/api/v1/payments/`
- `/api/v1/subscriptions/`
- `/api/v1/discounts/`
- `/api/v1/shipping/`
- `/api/v1/reviews/`
- `/api/v1/analytics/`
- `/api/v1/search/`

## Deployment on Hostinger VPS (No Docker)

Deployment artifacts:

- `deployment/nginx/kofora_api.conf`
- `deployment/systemd/kofora-gunicorn.service`
- `deployment/systemd/kofora-celery-worker.service`
- `deployment/systemd/kofora-celery-beat.service`
- `gunicorn.conf.py`

See `deployment/HOSTINGER_VPS_SETUP.md` for full deployment sequence.
