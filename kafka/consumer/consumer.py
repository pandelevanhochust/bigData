# consumer.py
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import requests
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransactionConsumer:
    def __init__(self, bootstrap_servers, api_endpoint='http://54.251.172.36:8000'):
        self.bootstrap_servers = bootstrap_servers
        self.api_endpoint = api_endpoint
        self.consumer = None
        self.max_retries = 5
        self.retry_delay = 10  # seconds

    def create_consumer(self):
        """Create Kafka consumer with better configuration"""
        try:
            self.consumer = KafkaConsumer(
                'transactions',
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
                group_id='fraud_detection_group',
                auto_offset_reset='earliest',  # Changed from 'latest' to get all messages
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                max_poll_records=10,
                consumer_timeout_ms=5000,  # Add timeout to prevent infinite blocking
                api_version=(0, 10, 1)  # Specify API version
            )
            logger.info("Kafka consumer created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            return False

    def test_kafka_connection(self):
        """Test connection to Kafka broker"""
        try:
            # Create a temporary consumer to test connection
            test_consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                consumer_timeout_ms=5000
            )

            # Try to get metadata
            metadata = test_consumer.list_consumer_groups()
            logger.info("Successfully connected to Kafka broker")
            test_consumer.close()
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Kafka broker: {e}")
            return False

    def test_api_connection(self):
        """Test connection to the API endpoint"""
        try:
            response = requests.get(f"{self.api_endpoint}/health", timeout=5)
            if response.status_code == 200:
                logger.info("API endpoint is accessible")
                return True
            else:
                logger.warning(f"API returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to API: {e}")
            return False

    def send_to_api(self, transaction):
        """Send transaction to FastAPI backend with retry logic"""
        max_api_retries = 3
        for attempt in range(max_api_retries):
            try:
                response = requests.post(
                    f"{self.api_endpoint}/api/transactions",
                    json=transaction,
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    logger.info(f"✓ Successfully sent to API: {transaction['transaction_id']}")
                    return True
                elif response.status_code == 422:
                    logger.error(f"Validation error for transaction {transaction['transaction_id']}: {response.text}")
                    return False  # Don't retry validation errors
                else:
                    logger.warning(f"API returned {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout sending to API (attempt {attempt + 1}/{max_api_retries})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error to API (attempt {attempt + 1}/{max_api_retries})")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")

            if attempt < max_api_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

        logger.error(f"Failed to send transaction {transaction['transaction_id']} after {max_api_retries} attempts")
        return False

    def validate_transaction(self, transaction):
        """Validate transaction data before sending to API"""
        required_fields = ['transaction_id', 'user_id', 'amount', 'merchant_id', 'timestamp']

        for field in required_fields:
            if field not in transaction:
                logger.error(f"Missing required field: {field}")
                return False

        if not isinstance(transaction.get('amount'), (int, float)):
            logger.error(f"Invalid amount type: {type(transaction.get('amount'))}")
            return False

        return True

    def start_consuming(self):
        """Start consuming transactions from Kafka with improved error handling"""
        logger.info("Starting Kafka consumer...")

        # Test connections first
        if not self.test_kafka_connection():
            logger.error("Cannot connect to Kafka broker. Exiting...")
            return

        if not self.test_api_connection():
            logger.warning("API endpoint test failed, but continuing...")

        retry_count = 0
        while retry_count < self.max_retries:
            try:
                if not self.create_consumer():
                    retry_count += 1
                    logger.warning(
                        f"Retrying consumer creation in {self.retry_delay} seconds... ({retry_count}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue

                logger.info("Consumer started successfully. Waiting for messages...")
                message_count = 0

                for message in self.consumer:
                    try:
                        transaction = message.value
                        message_count += 1

                        logger.info(
                            f"Received message #{message_count}: {transaction.get('transaction_id', 'Unknown ID')}")
                        logger.debug(
                            f"Message details - Topic: {message.topic}, Partition: {message.partition}, Offset: {message.offset}")

                        if self.validate_transaction(transaction):
                            self.send_to_api(transaction)
                        else:
                            logger.error(f"Invalid transaction data: {transaction}")

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode message JSON: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")

                    # Add a small delay to prevent overwhelming the API
                    time.sleep(0.1)

            except KafkaError as e:
                logger.error(f"Kafka error: {e}")
                retry_count += 1
                if retry_count < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds... ({retry_count}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                else:
                    logger.error("Max retries reached. Exiting...")
                    break

            except KeyboardInterrupt:
                logger.info("Received shutdown signal...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                retry_count += 1
                if retry_count < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    break
            finally:
                if self.consumer:
                    self.consumer.close()
                    logger.info("Consumer closed")

        logger.info("Consumer stopped")


if __name__ == "__main__":
    # Remove 'http://' from bootstrap servers - Kafka doesn't use HTTP protocol
    consumer = TransactionConsumer(
        bootstrap_servers=['13.228.128.157:9092'],  # Fixed: removed http://
        api_endpoint='http://54.251.172.36:8000'
    )
    consumer.start_consuming()