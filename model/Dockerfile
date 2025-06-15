#FROM python:3.10-slim
#
## Install system packages
#
## Install system packages
#RUN apt-get update && apt-get install -y \
#    build-essential \
#    libgomp1 \
#    supervisor \
#    && rm -rf /var/lib/apt/lists/*
#
## Set work directory
#WORKDIR /app
#
## Copy dependencies
#COPY requirements.txt .
#
## Install Python dependencies
#RUN pip install --upgrade pip && pip install -r requirements.txt
#
## Copy the app code
#COPY . .
#
## Expose API port
#EXPOSE 8000
#
## Start the API
#CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "fraud_detection:app", "--host", "0.0.0.0", "--port", "8000"]

