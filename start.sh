#!/bin/bash
pip install -r requirements.txt
python manage.py migrate
gunicorn ErisaProject.wsgi:application --bind 0.0.0.0:10000
