#!/bin/bash
source venv/bin/activate
exec gunicorn -b :8080 --access-logfile - --error-logfile - -w 12 wsgi:app
