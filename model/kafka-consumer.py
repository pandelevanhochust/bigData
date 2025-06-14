import json
import asyncio
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from loguru import logger
from typing import Dict, Any
import requests
from datetime import datetime
import uuid

from model.config import settings
from model.model_service import model_service
from model.schemas import PredictionInput, KafkaMessage

class KafkaConsumerService:
    def __init__(self):
        self.consumer = None
        self.running = False

    def create_consumer(self):
        """Create Kafka consumer"""
        try:
            self.consumer = KafkaConsumer(
                settings.kafka_topic_input,
                bootstrap_servers=settings.kafka_bootstrap_servers.split(','),
                group_id=settings.kafka_group_id,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                consumer_timeout_ms=1000
            )
            logger.info(f"Kafka consumer created for topic: {settings.kafka_topic_input}")
            return True
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer: {str(e)}")
            return False

    async def send_to_backend(self, prediction_result):
        """Send prediction result to backend API"""
        try:
            if not settings.backend_api_url:
                logger.warning("Backend API URL not configured")
                return

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {settings.backend_api_key}' if settings.backend_api_key else None
            }

            # Remove None values from headers
            headers = {k: v for k, v in headers.items() if v is not None}

            response = requests.post(
                settings.backend_api_url,
                json=prediction_result.dict(),
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Successfully sent prediction to backend: {prediction_result.prediction}")
            else:
                logger.error(f"Failed to send to backend. Status: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error sending to backend: {str(e)}")

    def process_message(self, message_value: Dict[str, Any]):
        """Process a single Kafka message"""
        try:
            # Create Kafka message object
            kafka_msg = KafkaMessage(
                data=message_value.get('data', message_value),
                message_id=message_value.get('message_id', str(uuid.uuid4())),
                timestamp=datetime.fromisoformat(message_value.get('timestamp', datetime.utcnow().isoformat())),
                source=message_value.get('source')
            )

            # Create prediction input
            prediction_input = PredictionInput(
                features=kafka_msg.data
            )

            # Make prediction
            prediction_result = model_service.predict(prediction_input)

            # Send to backend (run in event loop)
            asyncio.create_task(self.send_to_backend(prediction_result))

            logger.info(f"Processed message: {kafka_msg.message_id}")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    def start_consuming(self):
        """Start consuming messages from Kafka"""
        if not self.create_consumer():
            return

        self.running = True
        logger.info("Starting Kafka consumer...")

        try:
            while self.running:
                try:
                    # Poll for messages
                    message_batch = self.consumer.poll(timeout_ms=1000)

                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            if not self.running:
                                break
                            self.process_message(message.value)

                except KafkaError as e:
                    logger.error(f"Kafka error: {str(e)}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in consumer loop: {str(e)}")

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        finally:
            self.stop_consuming()

    def stop_consuming(self):
        """Stop consuming messages"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer stopped")

    def is_connected(self) -> bool:
        """Check if consumer is connected"""
        try:
            if self.consumer:
                return len(self.consumer.bootstrap_connected()) > 0
            return False
        except:
            return False

# Global consumer service instance
kafka_consumer_service = KafkaConsumerService()