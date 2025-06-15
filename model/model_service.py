import pickle
import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, Any, List

import config
from schemas import PredictionInput, PredictionOutput

settings = config.settings

class ModelService:
    def __init__(self):
        self.model = None
        self.feature_names = None
        self.model_version = "1.0"
        self.load_model()

    def load_model(self):
        try:
            with open(settings.model_path, 'rb') as f:
                self.model = pickle.load(f)
            if hasattr(self.model, 'feature_names_in_'):
                self.feature_names = self.model.feature_names_in_
            logger.info(f"Model loaded from {settings.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def preprocess_features(self, features: Dict[str, Any]) -> pd.DataFrame:
        try:
            df = pd.DataFrame([features]).fillna(0)
            if self.feature_names:
                for feature in set(self.feature_names) - set(df.columns):
                    df[feature] = 0
                df = df[self.feature_names]
            return df
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            raise

    def predict(self, prediction_input: PredictionInput) -> PredictionOutput:
        if not self.model:
            raise ValueError("Model not loaded")
        features = self.preprocess_features(prediction_input.features)
        prediction = self.model.predict(features)[0]
        probability = None
        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(features)[0]
            probability = proba.tolist()
        return PredictionOutput(prediction=float(prediction), probability=probability)

    def is_model_loaded(self):
        return self.model is not None

model_service = ModelService()
