import json
import time
from kafka import KafkaConsumer
from datetime import datetime
import requests
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os


class FraudDetectionModel:
    def __init__(self):
        self.model = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = 'fraud_model.pkl'
        self.scaler_path = 'scaler.pkl'

        # Try to load existing model
        self.load_model()

    def extract_features(self, transaction):
        """Extract numerical features from transaction for ML model"""
        features = [
            transaction['amount'],
            transaction['hour'],
            transaction['day_of_week'],
            1 if transaction['is_weekend'] else 0,
            transaction['previous_transaction_minutes'],
            transaction['account_balance'],
            len(transaction['merchant_category']),  # Category name length as feature
            1 if transaction['payment_method'] == 'Online' else 0,
            1 if transaction['card_type'] == 'Credit' else 0,
            abs(transaction['location']['lat']),  # Absolute latitude
            abs(transaction['location']['lon'])  # Absolute longitude
        ]
        return np.array(features).reshape(1, -1)

    def train_model(self, transactions):
        """Train the fraud detection model with historical data"""
        if len(transactions) < 50:  # Need minimum data for training
            return False

        features_list = []
        for transaction in transactions:
            features = self.extract_features(transaction)
            features_list.append(features.flatten())

        X = np.array(features_list)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True

        # Save model
        self.save_model()
        print(f"Model trained with {len(transactions)} transactions")
        return True

    def predict_fraud(self, transaction):
        """Predict if transaction is fraudulent"""
        if not self.is_trained:
            # Return default prediction if model not trained
            return {
                'is_fraud': False,
                'fraud_score': 0.5,
                'confidence': 'low'
            }

        features = self.extract_features(transaction)
        features_scaled = self.scaler.transform(features)

        # -1 for anomaly (fraud), 1 for normal
        prediction = self.model.predict(features_scaled)[0]

        # Get anomaly score (more negative = more anomalous)
        anomaly_score = self.model.decision_function(features_scaled)[0]

        # Convert to probability-like score (0-1, higher = more fraudulent)
        fraud_score = max(0, min(1, (0.5 - anomaly_score) / 1.0))

        is_fraud = prediction == -1
        confidence = 'high' if abs(anomaly_score) > 0.3 else 'medium' if abs(anomaly_score) > 0.1 else 'low'

        return {
            'is_fraud': is_fraud,
            'fraud_score': round(fraud_score, 3),
            'confidence': confidence,
            'anomaly_score': round(anomaly_score, 3)
        }

    def save_model(self):
        """Save trained model and scaler"""
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)

    def load_model(self):
        """Load trained model and scaler"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
                print("Loaded existing fraud detection model")
        except Exception as e:
            print(f"Could not load existing model: {e}")


class TransactionConsumer:
    def __init__(self, bootstrap_servers=['localhost:9092'], api_endpoint='http://localhost:8000'):
        self.consumer = KafkaConsumer(
            'transactions',
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            key_deserializer=lambda x: x.decode('utf-8') if x else None,
            group_id='fraud_detection_group',
            auto_offset_reset='latest'
        )
        self.fraud_model = FraudDetectionModel()
        self.api_endpoint = api_endpoint
        self.processed_transactions = []

    def send_to_api(self, transaction_with_prediction):
        """Send processed transaction to FastAPI backend"""
        try:
            response = requests.post(
                f"{self.api_endpoint}/api/transactions",
                json=transaction_with_prediction,
                timeout=5
            )
            if response.status_code == 200:
                return True
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Failed to send to API: {e}")
            return False

    def process_transaction(self, transaction):
        """Process transaction through fraud detection"""
        # Get fraud prediction
        fraud_prediction = self.fraud_model.predict_fraud(transaction)

        # Combine transaction with prediction
        result = {
            **transaction,
            'fraud_prediction': fraud_prediction,
            'processed_at': datetime.now().isoformat(),
            'processing_time_ms': 50  # Simulated processing time
        }

        # Store for model retraining
        self.processed_transactions.append(transaction)

        # Retrain model periodically
        if len(self.processed_transactions) % 100 == 0:
            print("Retraining fraud detection model...")
            self.fraud_model.train_model(self.processed_transactions[-200:])  # Use last 200 transactions

        return result

    def start_consuming(self):
        """Start consuming transactions from Kafka"""
        print("Starting fraud detection consumer...")
        print(f"API endpoint: {self.api_endpoint}")

        try:
            for message in self.consumer:
                transaction = message.value
                print(f"Processing transaction: {transaction['transaction_id']}")

                # Process through fraud detection
                processed_transaction = self.process_transaction(transaction)

                # Send to API
                success = self.send_to_api(processed_transaction)

                if success:
                    fraud_status = "FRAUD" if processed_transaction['fraud_prediction']['is_fraud'] else "NORMAL"
                    score = processed_transaction['fraud_prediction']['fraud_score']
                    print(f"✓ Sent to API - Status: {fraud_status}, Score: {score}")
                else:
                    print("✗ Failed to send to API")

        except KeyboardInterrupt:
            print("Stopping consumer...")
        finally:
            self.consumer.close()


if __name__ == "__main__":
    # Replace with your EC2 addresses
    consumer = TransactionConsumer(
        bootstrap_servers=['your-ec2-kafka-broker:9092'],
        api_endpoint='http://your-ec2-fastapi-server:8000'
    )
    consumer.start_consuming()