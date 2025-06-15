import xgboost as xgb
import pandas as pd
from loguru import logger
from typing import Dict, Any

import config
from schemas import PredictionInput, PredictionOutput

settings = config.settings

class ModelService:
    def __init__(self):
        self.model: xgb.Booster = None
        self.feature_names = None
        self.model_version = "1.0"
        self.load_model()

    def load_model(self):
        try:
            self.model = xgb.Booster()
            self.model.load_model(settings.model_path)
            logger.info(f"Model loaded from {settings.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def preprocess_features(self, features: Dict[str, Any]) -> pd.DataFrame:
        try:
            # Remove non-numeric / ID fields that are not used by the model
            exclude = ['transaction_id', 'user_id', 'timestamp']
            features_cleaned = {k: v for k, v in features.items() if k not in exclude}

            df = pd.DataFrame([features_cleaned]).fillna(0)

            # Ensure correct order of features
            if self.feature_names:
                for feature in set(self.feature_names) - set(df.columns):
                    df[feature] = 0  # Fill missing columns with 0
                df = df[self.feature_names]

            return df
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            raise

    def predict(self, prediction_input: PredictionInput) -> PredictionOutput:
        if not self.model:
            raise ValueError("Model not loaded")
        dmatrix = self.preprocess_features(prediction_input.features)
        pred_probs = self.model.predict(dmatrix)
        prediction = float(pred_probs[0] > 0.5)
        return PredictionOutput(prediction=prediction, probability=pred_probs.tolist())

    def is_model_loaded(self):
        return self.model is not None

model_service = ModelService()
