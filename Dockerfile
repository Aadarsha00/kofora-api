FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libpq5 = runtime lib for psycopg (binary wheel still needs the shared lib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system django && adduser --system --ingroup django --home /home/django django \
    && mkdir -p /home/django \
    && chown -R django:django /home/django \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R django:django /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
