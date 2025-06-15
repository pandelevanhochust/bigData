import json
import logging
import os

import pandas as pd
import requests
import time
from kafka import KafkaConsumer

KAFKA_BROKER = os.getenv('KAFKA_BROKERS', '13.228.128.157:9092')
TOPIC = 'transactions'
API_ENDPOINT = os.getenv('API_ENDPOINT', 'http://54.251.172.36:8000/api/transactions')
API__MODEL_ENDPOINT = os.getenv('API__MODEL_ENDPOINT', 'http://13.214.239.8:8000/api/transactions')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
# scaler = joblib.load("scaler.pkl")

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

def post_to_api_model(xscale):
    try:
        response = requests.post(API__MODEL_ENDPOINT, json={"features": xscale}, timeout=5)
        logger.info(f"POST status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logger.error(f"Error posting to API: {e}")

def preprocessing(txn):
    drop_cols = ['local_timestamp', 'time', 'date', 'IP', 'device_id', 'merchant_id']
    txn = {k: v for k, v in txn.items() if k not in drop_cols}

    # 2. Ensure required fields are present
    categorical_cols = [
        'currency', 'payment_channel', 'card_present', 'card_entry_mode',
        'auth_result', 'tokenised', 'recurring_flag', 'cross_border',
        'auth_characteristics', 'message_type', 'merchant_country',
        'pin_verif_method', 'term_location'
    ]

    df = pd.DataFrame([txn])

    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                df[col] = df[col].str.replace(',', '.').astype(float)
            except:
                pass
    df = pd.get_dummies(df, columns=[col for col in categorical_cols if col in df.columns], drop_first=True)
    return df.fillna(0).values.tolist()[0]  # or simply df.to_dict() if model expects JSON


def start_consuming():
    logger.info(f"Listening on topic '{TOPIC}' from broker '{KAFKA_BROKER}'")
    for message in consumer:
        txn = message.value
        logger.info(f"Received: {txn.get('transaction_id', '[no id]')}")

        if is_valid_transaction(txn):
            # post_to_api(txn)
            xscale = preprocessing(txn)
            post_to_api_model(xscale)

        else:
            logger.warning(f"Invalid transaction skipped: {txn}")

        time.sleep(0.1)  # throttle to avoid flooding API


if __name__ == '__main__':
    start_consuming()
