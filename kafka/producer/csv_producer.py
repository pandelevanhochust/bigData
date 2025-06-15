# csv_producer.py
import csv
import json
import time
import logging
from kafka import KafkaProducer

# === CONFIG ===
KAFKA_BROKER = '13.228.128.157:9092'
TOPIC = 'transactions'
CSV_FILE = 'data_train.csv'  # Your actual CSV filename
DELAY_BETWEEN_MESSAGES = 1  # seconds

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# === KAFKA PRODUCER ===
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
)

# === FUNCTION TO CLEAN FIELDS ===
def clean_row(row):
    row["transaction_id"] = f"{row.get('device_id', 'unknown')}_{int(time.time()*1000)}"
    row["user_id"] = row.get("device_id", "unknown")
    row["timestamp"] = f"{row.get('date', '')}T{row.get('time', '')}"

    return row

# === MAIN FUNCTION ===
def send_csv_to_kafka():
    logger.info("Starting to stream transactions from CSV to Kafka...")

    with open(CSV_FILE, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            txn = clean_row(row)

            try:
                producer.send(TOPIC, value=txn)
                logger.info(f"[✓] Sent transaction #{i+1} - {txn['transaction_id']}")
            except Exception as e:
                logger.error(f"[✗] Failed to send transaction #{i+1}: {e}")

            time.sleep(DELAY_BETWEEN_MESSAGES)

    producer.flush()
    logger.info("✅ Finished sending all transactions.")

# === ENTRYPOINT ===
if __name__ == "__main__":
    send_csv_to_kafka()
