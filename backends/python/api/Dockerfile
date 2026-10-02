# ---------- Base stage ----------
FROM python:3.11-slim AS base

WORKDIR /var/www/api

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ---------- Development stage ----------
FROM base AS dev
ENV DJANGO_ENV=development \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------- Production stage ----------
FROM base AS prod
ENV DJANGO_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "gunicorn wsgi:application \
       --bind 0.0.0.0:${PORT} \
       --workers 2 \
       --timeout 120 \
       --access-logfile - \
       --error-logfile -"]
