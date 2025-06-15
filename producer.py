# producer.py
import json
import time
import random
import logging
import os
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
from faker import Faker
import uuid

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

fake = Faker()


class TransactionProducer:
    def __init__(self, bootstrap_servers):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.topic = 'transactions'
        self.create_producer()

    def create_producer(self):
        """Create Kafka producer with better configuration"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                batch_size=16384,
                linger_ms=10,
                buffer_memory=33554432,
                max_request_size=1048576,
                api_version=(0, 10, 1)
            )
            logger.info("Kafka producer created successfully")

            # Test connection by getting metadata
            metadata = self.producer.partitions_for(self.topic)
            if metadata is not None:
                logger.info(f"Topic '{self.topic}' has {len(metadata)} partitions")
            else:
                logger.warning(f"Topic '{self.topic}' might not exist yet")

        except Exception as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            raise

    def generate_transaction(self):
        """Generate realistic transaction data"""
        transaction_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        merchant_id = str(uuid.uuid4())

        # Generate transaction with some fraud indicators
        is_suspicious = random.random() < 0.1  # 10% suspicious transactions
        current_time = datetime.now()

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
            'user_id': user_id,
            'amount': round(amount, 2),
            'merchant_id': merchant_id,
            'merchant_category': merchant_category,
            'location': {
                'city': fake.city(),
                'country': fake.country_code(),
                'lat': float(fake.latitude()),
                'lon': float(fake.longitude())
            },
            'timestamp': current_time.isoformat(),
            'card_type': random.choice(['Credit', 'Debit']),
            'payment_method': random.choice(['Chip', 'Swipe', 'Contactless', 'Online']),
            'hour': hour,
            'day_of_week': current_time.weekday(),
            'is_weekend': current_time.weekday() >= 5,
            'previous_transaction_minutes': random.randint(1, 1440),  # Minutes since last transaction
            'account_balance': round(random.uniform(100, 10000), 2),
            'is_suspicious': is_suspicious  # Add flag for testing
        }

        return transaction

    def send_transaction(self, transaction):
        """Send transaction to Kafka topic with better error handling"""
        try:
            future = self.producer.send(
                self.topic,
                key=transaction['transaction_id'],
                value=transaction
            )

            # Get the result to ensure the message was sent
            record_metadata = future.get(timeout=30)

            logger.info(
                f"✓ Sent transaction {transaction['transaction_id']} "
                f"to partition {record_metadata.partition} "
                f"at offset {record_metadata.offset}"
            )
            return True

        except KafkaError as e:
            logger.error(f"Kafka error sending transaction {transaction['transaction_id']}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending transaction {transaction['transaction_id']}: {e}")
            return False

    def start_streaming(self, interval=2, max_messages=None):
        """Start continuous transaction streaming"""
        logger.info(f"Starting transaction stream to topic '{self.topic}' every {interval} seconds...")

        if max_messages:
            logger.info(f"Will send maximum {max_messages} messages")

        message_count = 0
        successful_sends = 0

        try:
            while True:
                if max_messages and message_count >= max_messages:
                    logger.info(f"Reached maximum message count: {max_messages}")
                    break

                transaction = self.generate_transaction()
                success = self.send_transaction(transaction)

                message_count += 1
                if success:
                    successful_sends += 1
                    logger.info(
                        f"Transaction #{message_count}: ${transaction['amount']} "
                        f"at {transaction['merchant_category']} "
                        f"({'SUSPICIOUS' if transaction['is_suspicious'] else 'NORMAL'})"
                    )

                # Log statistics every 10 messages
                if message_count % 10 == 0:
                    success_rate = (successful_sends / message_count) * 100
                    logger.info(
                        f"Statistics: {successful_sends}/{message_count} sent successfully ({success_rate:.1f}%)")

                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal...")
        except Exception as e:
            logger.error(f"Unexpected error in streaming: {e}")
        finally:
            if self.producer:
                logger.info("Flushing remaining messages...")
                self.producer.flush()
                self.producer.close()
                logger.info(
                    f"Producer stopped. Final stats: {successful_sends}/{message_count} messages sent successfully")


if __name__ == "__main__":
    # Get Kafka brokers from environment variable or use default
    kafka_brokers = os.getenv('KAFKA_BROKERS', '13.228.128.157:9092').split(',')
    logger.info(f"Using Kafka brokers: {kafka_brokers}")

    producer = TransactionProducer(bootstrap_servers=kafka_brokers)
    producer.start_streaming(interval=1)  # Send transaction every second