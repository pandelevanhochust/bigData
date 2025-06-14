import pickle
import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, Any, List
import xgboost as xgb
from model.config import settings
from model.schemas import PredictionInput, PredictionOutput
from datetime import datetime


class ModelService:
    def __init__(self):
        self.model = None
        self.feature_names = None
        self.model_version = "1.0"
        self.load_model()

    def load_model(self):
        """Load the XGBoost model from pickle file"""
        try:
            with open(settings.model_path, 'rb') as f:
                self.model = pickle.load(f)

            # If your model has feature names, extract them
            if hasattr(self.model, 'feature_names_in_'):
                self.feature_names = self.model.feature_names_in_

            logger.info(f"Model loaded successfully from {settings.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False

    def preprocess_features(self, features: Dict[str, Any]) -> pd.DataFrame:
        """
        Preprocess input features for model prediction
        Adjust this method based on your specific preprocessing needs
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame([features])

            # Handle missing values
            df = df.fillna(0)

            # Ensure feature order matches training data
            if self.feature_names is not None:
                # Reorder columns to match training data
                missing_features = set(self.feature_names) - set(df.columns)
                if missing_features:
                    logger.warning(f"Missing features: {missing_features}")
                    # Add missing features with default values
                    for feature in missing_features:
                        df[feature] = 0

                # Select and reorder features
                df = df[self.feature_names]

            return df

        except Exception as e:
            logger.error(f"Error in preprocessing: {str(e)}")
            raise

    def predict(self, prediction_input: PredictionInput) -> PredictionOutput:
        """Make prediction using the loaded model"""
        try:
            if self.model is None:
                raise ValueError("Model not loaded")

            # Preprocess features
            processed_features = self.preprocess_features(prediction_input.features)

            # Make prediction
            prediction = self.model.predict(processed_features)[0]

            # Get prediction probabilities if it's a classifier
            probabilities = None
            confidence_score = None

            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(processed_features)[0]
                probabilities = proba.tolist()
                confidence_score = float(max(proba))

            # Create response
            result = PredictionOutput(
                prediction=float(prediction),
                probability=probabilities
            )

            logger.info(f"Prediction made: {prediction}")
            return result

        except Exception as e:
            logger.error(f"Error in prediction: {str(e)}")
            raise

    def is_model_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model is not None


# Global model service instance
model_service = ModelService()