FROM php:8.0-apache

RUN docker-php-ext-install mysqli
RUN a2enmod rewrite

ADD . /var/www/html