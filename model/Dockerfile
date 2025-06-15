FROM python:3.10-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get install -y supervisor

# Set work directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the app code
COPY . .

# Expose API port
EXPOSE 8000

# Start the API
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
