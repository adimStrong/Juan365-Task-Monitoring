FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies (psycopg2-binary doesn't need libpq-dev)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "ticketing.wsgi:application", "--bind", "0.0.0.0:8000"]
