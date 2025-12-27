FROM python:3.11-slim

# Cache bust argument - change date to force rebuild
ARG CACHE_DATE=2025-12-27

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend project files
COPY backend/ .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn with gevent workers for better concurrency
CMD python manage.py migrate --noinput && gunicorn -k gevent -w 4 --timeout 120 ticketing.wsgi:application --bind 0.0.0.0:8000
