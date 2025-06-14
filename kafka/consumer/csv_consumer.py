import json
import logging
import os
import requests
import time
from kafka import KafkaConsumer

# === CONFIG ===
KAFKA_BROKER = os.getenv('KAFKA_BROKERS', '13.228.128.157:9092')
TOPIC = 'transactions'
API_ENDPOINT = os.getenv('API_ENDPOINT', 'http://54.251.172.36:8000')  # adjust if needed

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# === KAFKA CONSUMER ===
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    group_id='csv_consumer_group',
    enable_auto_commit=True
)


def is_valid_transaction(txn):
    required = ['transaction_id', 'user_id', 'amount', 'merchant_id', 'timestamp']
    return all(k in txn for k in required)


def post_to_api(txn):
    try:
        response = requests.post(API_ENDPOINT, json=txn, timeout=5)
        if response.status_code == 200:
            logger.info(f"[✓] Sent {txn['transaction_id']} to API")
        else:
            logger.warning(f"[!] API {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"[✗] Failed to send to API: {e}")


def start_consuming():
    logger.info(f"Listening on topic '{TOPIC}' from broker '{KAFKA_BROKER}'")
    for message in consumer:
        txn = message.value
        logger.info(f"Received: {txn.get('transaction_id', '[no id]')}")

        if is_valid_transaction(txn):
            post_to_api(txn)
        else:
            logger.warning(f"Invalid transaction skipped: {txn}")

        time.sleep(0.1)  # throttle to avoid flooding API


if __name__ == '__main__':
    start_consuming()
