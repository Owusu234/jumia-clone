#!/bin/bash
set -e
echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "Running migrations..."
python manage.py migrate
echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
