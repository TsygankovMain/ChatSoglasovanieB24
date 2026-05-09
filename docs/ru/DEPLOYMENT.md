# Руководство по развертыванию

Полное руководство по развертыванию приложения на продакшене.

## Предварительная проверка

- [ ] Все тесты проходят
- [ ] Аудит безопасности пройден
- [ ] Переменные окружения настроены
- [ ] Миграции БД протестированы
- [ ] SSL сертификаты получены
- [ ] Приложение зарегистрировано в Bitrix24
- [ ] API протестирован с реальным порталом
- [ ] Мониторинг и логирование настроены

## Требования сервера

**Минимум**:
- 2 CPU ядра
- 4 GB RAM
- 20 GB диск
- Ubuntu 20.04 LTS

**Рекомендуется**:
- 4+ CPU ядер
- 8+ GB RAM
- 50+ GB диск
- Auto-scaling

## Установка зависимостей

```bash
# Обновление системы
sudo apt-get update && sudo apt-get upgrade -y

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Переменные окружения

**.env для продакшена**:
```bash
VIRTUAL_HOST=https://approval.yourdomain.com
NUXT_PUBLIC_APP_URL=https://approval.yourdomain.com
NUXT_PUBLIC_API_URL=https://approval.yourdomain.com/api
SERVER_HOST=http://api-python:8000

CLIENT_ID=your_app_client_id
CLIENT_SECRET=your_app_client_secret
SCOPE=im,imbot,entity,disk,placement,user

DB_NAME=approval_db
DB_USER=approval_user
DB_PASSWORD=very_secure_password
DB_HOST=database

NODE_ENV=production
BUILD_TARGET=prod
```

## Docker Compose развертывание

```bash
# Клонируем репозиторий
sudo mkdir -p /var/www/approval-app
cd /var/www/approval-app
git clone <repo-url> .

# Копируем .env
cp .env.example .env
# Редактируем .env

# Запуск сервисов
docker-compose -f docker-compose.prod.yml up -d --build

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps

# Логи
docker-compose -f docker-compose.prod.yml logs -f
```

## SSL/HTTPS (Let's Encrypt)

```bash
# Установка Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Получение сертификата
sudo certbot certonly --standalone \
  -d approval.yourdomain.com \
  --agree-tos \
  --email your-email@domain.com

# Сертификаты в: /etc/letsencrypt/live/approval.yourdomain.com/
```

## Nginx конфигурация

```nginx
# Редирект HTTP на HTTPS
server {
    listen 80;
    server_name approval.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name approval.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/approval.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/approval.yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Фронтенд
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://api-python:8000;
        proxy_read_timeout 30s;
    }
}
```

## Мониторинг здоровья

Services имеют встроенные healthchecks:

```bash
# Проверка статуса
docker-compose -f docker-compose.prod.yml ps

# Должны показывать "healthy"
```

## Резервное копирование БД

```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/approval-db"
mkdir -p $BACKUP_DIR

docker-compose -f /var/www/approval-app/docker-compose.prod.yml exec -T database \
  pg_dump -U approval_user approval_db | gzip > $BACKUP_DIR/db-$TIMESTAMP.sql.gz

# Сохранение на 7 дней
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

## Масштабирование

### Docker Swarm

```bash
docker swarm init
docker service create --replicas 3 api-python
```

### Database Connection Pooling

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,
    "max_overflow": 40,
    "pool_pre_ping": True,
}
```

## Откат на предыдущую версию

```bash
# Тегируем текущую версию
git tag backup-production-$(date +%Y%m%d)

# Переходим на предыдущую
git checkout tags/v1.0.0

# Перестраиваем
docker-compose -f docker-compose.prod.yml up -d --build

# Проверяем логи
docker-compose -f docker-compose.prod.yml logs -f
```

## Решение проблем

### Сервисы не запускаются

```bash
docker-compose -f docker-compose.prod.yml logs
docker-compose -f docker-compose.prod.yml up -d --build
```

### Ошибки БД

```bash
# Проверка здоровья
docker-compose -f docker-compose.prod.yml exec database pg_isready

# Подключение вручную
docker-compose -f docker-compose.prod.yml exec database \
  psql -U approval_user -d approval_db
```

### Проблемы с SSL

```bash
# Проверка срока действия
sudo openssl x509 -in /etc/letsencrypt/live/approval.yourdomain.com/cert.pem -noout -dates

# Обновление
sudo certbot renew --force-renewal
```

---

**Последнее обновление**: Апрель 2026
