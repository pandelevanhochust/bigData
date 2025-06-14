# debug_kafka.py
"""
Debugging tools for Kafka connectivity and message flow
"""
import json
import logging
from kafka import KafkaConsumer, KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError
import requests
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KafkaDebugger:
    def __init__(self, bootstrap_servers, api_endpoint):
        self.bootstrap_servers = bootstrap_servers
        self.api_endpoint = api_endpoint

    def test_kafka_connection(self):
        """Test basic Kafka broker connectivity"""
        logger.info("Testing Kafka broker connectivity...")
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id='debug_client'
            )

            # Get cluster metadata
            metadata = admin_client.describe_cluster()
            logger.info(f"✓ Connected to Kafka cluster: {len(metadata)} brokers")

            # List topics
            topics = admin_client.list_topics()
            logger.info(f"✓ Available topics: {list(topics)}")

            admin_client.close()
            return True

        except Exception as e:
            logger.error(f"✗ Kafka connection failed: {e}")
            return False

    def test_api_connection(self):
        """Test API endpoint connectivity"""
        logger.info("Testing API endpoint connectivity...")

        # Test basic connectivity
        try:
            response = requests.get(f"{self.api_endpoint}/docs", timeout=10)
            logger.info(f"✓ API docs accessible: {response.status_code}")
        except Exception as e:
            logger.error(f"✗ API docs not accessible: {e}")

        # Test health endpoint
        try:
            response = requests.get(f"{self.api_endpoint}/health", timeout=10)
            logger.info(f"✓ Health endpoint: {response.status_code}")
        except Exception as e:
            logger.warning(f"Health endpoint not available: {e}")

        # Test transactions endpoint with sample data
        sample_transaction = {
            "transaction_id": "test-123",
            "user_id": "user-123",
            "amount": 100.0,
            "merchant_id": "merchant-123",
            "timestamp": "2025-06-14T10:00:00"
        }

        try:
            response = requests.post(
                f"{self.api_endpoint}/api/transactions",
                json=sample_transaction,
                timeout=10
            )
            logger.info(f"✓ Transactions endpoint test: {response.status_code}")
            if response.status_code != 200:
                logger.warning(f"Response: {response.text}")
            return True
        except Exception as e:
            logger.error(f"✗ Transactions endpoint failed: {e}")
            return False

    def create_topic_if_not_exists(self, topic_name='transactions'):
        """Create Kafka topic if it doesn't exist"""
        logger.info(f"Checking/creating topic: {topic_name}")
        try:
            admin_client = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)

            # Check if topic exists
            existing_topics = admin_client.list_topics()
            if topic_name in existing_topics:
                logger.info(f"✓ Topic '{topic_name}' already exists")
            else:
                # Create topic
                topic = NewTopic(
                    name=topic_name,
                    num_partitions=3,
                    replication_factor=1
                )
                admin_client.create_topics([topic])
                logger.info(f"✓ Created topic '{topic_name}'")

            admin_client.close()
            return True

        except Exception as e:
            logger.error(f"✗ Topic creation failed: {e}")
            return False

    def test_producer(self, num_messages=5):
        """Test producing messages to Kafka"""
        logger.info(f"Testing producer with {num_messages} messages...")
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8')
            )

            for i in range(num_messages):
                test_message = {
                    'transaction_id': f'test-{i}',
                    'amount': 100.0 + i,
                    'timestamp': time.time()
                }

                future = producer.send('transactions', key=f'test-{i}', value=test_message)
                record_metadata = future.get(timeout=10)

                logger.info(f"✓ Sent test message {i} to partition {record_metadata.partition}")

            producer.close()
            logger.info("✓ Producer test completed successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Producer test failed: {e}")
            return False

    def test_consumer(self, timeout_seconds=30):
        """Test consuming messages from Kafka"""
        logger.info(f"Testing consumer for {timeout_seconds} seconds...")
        try:
            consumer = KafkaConsumer(
                'transactions',
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest',
                consumer_timeout_ms=timeout_seconds * 1000,
                group_id='debug_group'
            )

            message_count = 0
            start_time = time.time()

            for message in consumer:
                message_count += 1
                logger.info(f"✓ Received message {message_count}: {message.value.get('transaction_id', 'No ID')}")

                if time.time() - start_time > timeout_seconds:
                    break

            consumer.close()
            logger.info(f"✓ Consumer test completed. Received {message_count} messages")
            return message_count > 0

        except Exception as e:
            logger.error(f"✗ Consumer test failed: {e}")
            return False

    def full_integration_test(self):
        """Run complete integration test"""
        logger.info("=" * 50)
        logger.info("STARTING FULL INTEGRATION TEST")
        logger.info("=" * 50)

        # Step 1: Test Kafka connectivity
        if not self.test_kafka_connection():
            logger.error("❌ Kafka connectivity failed - stopping test")
            return False

        # Step 2: Test API connectivity
        if not self.test_api_connection():
            logger.error("❌ API connectivity failed - stopping test")
            return False

        # Step 3: Create topic
        if not self.create_topic_if_not_exists():
            logger.error("❌ Topic creation failed - stopping test")
            return False

        # Step 4: Test producer
        if not self.test_producer():
            logger.error("❌ Producer test failed - stopping test")
            return False

        # Step 5: Test consumer
        if not self.test_consumer(timeout_seconds=10):
            logger.warning("⚠️  Consumer test didn't receive messages (this might be normal)")

        logger.info("=" * 50)
        logger.info("✅ INTEGRATION TEST COMPLETED")
        logger.info("=" * 50)
        return True


def main():
    # Configuration
    KAFKA_BROKERS = ['13.228.128.157:9092']  # Fixed: removed http://
    API_ENDPOINT = 'http://54.251.172.36:8000'

    debugger = KafkaDebugger(KAFKA_BROKERS, API_ENDPOINT)
    debugger.full_integration_test()


if __name__ == "__main__":
    main()