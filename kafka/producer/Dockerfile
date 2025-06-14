FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install kafka-python faker requests
CMD ["python", "producer.py"]
