FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY consumer.py .

# Optional: If you want to use debug_kafka.py in same image
COPY ../debug_kafka.py .

# Health check (connect to Kafka broker)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import socket; socket.socket().connect(('13.228.128.157', 9092))" || exit 1

CMD ["python", "consumer.py"]
