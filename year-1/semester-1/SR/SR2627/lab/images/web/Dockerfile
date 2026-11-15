# Intentionally vulnerable target for L7 attacks (role 4). Lab only.
FROM php:8.2-apache

RUN apt-get update && apt-get install -y --no-install-recommends \
        libmariadb-dev \
        curl iproute2 \
    && docker-php-ext-install mysqli \
    && rm -rf /var/lib/apt/lists/*

# The app is bind-mounted during development; this copy keeps the image
# self-contained if someone runs it without the mount.
COPY web/ /var/www/html/

EXPOSE 80
