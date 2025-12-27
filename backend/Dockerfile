FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for gevent (C extension)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies to reduce image size
RUN apt-get purge -y gcc libc-dev && apt-get autoremove -y

# Copy backend project files
COPY backend/ .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn with gevent workers for better concurrency
CMD python manage.py migrate --noinput && gunicorn -k gevent -w 4 --timeout 120 ticketing.wsgi:application --bind 0.0.0.0:8000
