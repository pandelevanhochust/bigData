# consumer.py
import json
from datetime import datetime
from kafka import KafkaConsumer
import requests


class TransactionConsumer:
    def __init__(self, bootstrap_servers, api_endpoint='http://localhost:8000'):
        self.consumer = KafkaConsumer(
            'transactions',
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            key_deserializer=lambda x: x.decode('utf-8') if x else None,
            group_id='fraud_detection_group',
            auto_offset_reset='latest'
        )
        self.api_endpoint = api_endpoint

    def send_to_api(self, transaction):
        """Send transaction to FastAPI backend"""
        try:
            response = requests.post(
                f"{self.api_endpoint}/api/transactions",
                json=transaction,
                timeout=5
            )
            if response.status_code == 200:
                print(f"✓ Sent to API: {transaction['transaction_id']}")
            else:
                print(f"API Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send to API: {e}")

    def start_consuming(self):
        """Start consuming transactions from Kafka"""
        print("Starting consumer...")

        try:
            for message in self.consumer:
                transaction = message.value
                print(f"Received transaction: {transaction['transaction_id']}")
                self.send_to_api(transaction)

        except KeyboardInterrupt:
            print("Stopping consumer...")
        finally:
            self.consumer.close()


if __name__ == "__main__":
    consumer = TransactionConsumer(
        bootstrap_servers=['kafka:9092'],
        api_endpoint='http://backend:8000'
    )
    consumer.start_consuming()
