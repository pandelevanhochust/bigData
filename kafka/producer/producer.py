import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer
from faker import Faker
import uuid

fake = Faker()


class TransactionProducer:
    def __init__(self, bootstrap_servers):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            key_serializer=lambda x: x.encode('utf-8') if x else None
        )
        self.topic = 'transactions'

    def generate_transaction(self):
        """Generate realistic transaction data"""
        transaction_id = str(uuid.uuid4())

        # Generate transaction with some fraud indicators
        is_suspicious = random.random() < 0.1  # 10% suspicious transactions

        if is_suspicious:
            amount = random.uniform(1000, 50000)  # Large amounts
            merchant_category = random.choice(['Online Casino', 'Unknown', 'High Risk'])
            hour = random.choice([2, 3, 4, 23, 0, 1])  # Unusual hours
        else:
            amount = random.uniform(5, 500)  # Normal amounts
            merchant_category = random.choice(['Grocery', 'Gas Station', 'Restaurant', 'Retail', 'Pharmacy'])
            hour = random.choice(list(range(8, 22)))  # Normal business hours

        transaction = {
            'transaction_id': transaction_id,
            'user_id': fake.uuid4(),
            'amount': round(amount, 2),
            'merchant_id': fake.uuid4(),
            'merchant_category': merchant_category,
            'location': {
                'city': fake.city(),
                'country': fake.country_code(),
                'lat': float(fake.latitude()),
                'lon': float(fake.longitude())
            },
            'timestamp': datetime.now().isoformat(),
            'card_type': random.choice(['Credit', 'Debit']),
            'payment_method': random.choice(['Chip', 'Swipe', 'Contactless', 'Online']),
            'hour': hour,
            'day_of_week': datetime.now().weekday(),
            'is_weekend': datetime.now().weekday() >= 5,
            'previous_transaction_minutes': random.randint(1, 1440),  # Minutes since last transaction
            'account_balance': round(random.uniform(100, 10000), 2)
        }

        return transaction

    def send_transaction(self, transaction):
        """Send transaction to Kafka topic"""
        try:
            future = self.producer.send(
                self.topic,
                key=transaction['transaction_id'],
                value=transaction
            )
            # Block for 'synchronous' sends
            record_metadata = future.get(timeout=10)
            print(
                f"Sent transaction {transaction['transaction_id']} to {record_metadata.topic} partition {record_metadata.partition}")
            return True
        except Exception as e:
            print(f"Error sending transaction: {e}")
            return False

    def start_streaming(self, interval=2):
        """Start continuous transaction streaming"""
        print(f"Starting transaction stream to topic '{self.topic}'...")
        try:
            while True:
                transaction = self.generate_transaction()
                success = self.send_transaction(transaction)
                if success:
                    print(f"Transaction: ${transaction['amount']} at {transaction['merchant_category']}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Stopping transaction stream...")
        finally:
            self.producer.close()


if __name__ == "__main__":
    producer = TransactionProducer(bootstrap_servers=['http://13.228.128.157:9092'])
    producer.start_streaming(interval=1)  # Send transaction every second