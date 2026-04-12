# Hostinger VPS Deployment Guide (Ubuntu, No Docker)

## 1. Provision Server Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib redis-server nginx git
```

## 2. Create App User and Directories

```bash
sudo mkdir -p /var/www/kofora
sudo chown -R $USER:$USER /var/www/kofora
cd /var/www/kofora
git clone <your-repo-url> backend
```

## 3. Python Environment

```bash
cd /var/www/kofora
python3 -m venv venv
source venv/bin/activate
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. PostgreSQL Setup

```bash
sudo -u postgres psql
```

Inside psql:

```sql
CREATE DATABASE kofora_db;
CREATE USER kofora_user WITH PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE kofora_db TO kofora_user;
\q
```

## 5. Environment Variables

```bash
cd /var/www/kofora/backend
cp .env.example .env
nano .env
```

Set production values:

- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=api.kofora.com`
- `DATABASE_URL=postgresql://...`
- Redis/Celery URLs
- Stripe/PayPal secrets
- SMTP credentials

## 6. Django Setup

```bash
source /var/www/kofora/venv/bin/activate
cd /var/www/kofora/backend
export DJANGO_SETTINGS_MODULE=kofora_backend.settings.production
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 7. systemd Services

Copy service files:

```bash
sudo cp deployment/systemd/kofora-gunicorn.service /etc/systemd/system/
sudo cp deployment/systemd/kofora-celery-worker.service /etc/systemd/system/
sudo cp deployment/systemd/kofora-celery-beat.service /etc/systemd/system/
```

Reload and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kofora-gunicorn kofora-celery-worker kofora-celery-beat
sudo systemctl start kofora-gunicorn kofora-celery-worker kofora-celery-beat
sudo systemctl status kofora-gunicorn
```

## 8. Nginx

```bash
sudo cp deployment/nginx/kofora_api.conf /etc/nginx/sites-available/kofora_api
sudo ln -s /etc/nginx/sites-available/kofora_api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 9. HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.kofora.com
```

## 10. Operational Checks

- `sudo systemctl status redis`
- `sudo systemctl status kofora-gunicorn`
- `sudo systemctl status kofora-celery-worker`
- `sudo systemctl status kofora-celery-beat`
- `curl https://api.kofora.com/api/v1/search/products/`

## 11. Media Strategy (Local now, R2 ready later)

Current setup stores media at `/var/www/kofora/backend/media`.
To migrate later to Cloudflare R2, replace Django storage backend and keep model schema unchanged.
