from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import sqlite3
import threading
from contextlib import contextmanager
import uvicorn

app = FastAPI(title="Fraud Detection API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = "fraud_detection.db"
db_lock = threading.Lock()
def init_database():
    """Initialize SQLite database"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                merchant_id TEXT NOT NULL,
                merchant_category TEXT NOT NULL,
                location_city TEXT,
                location_country TEXT,
                location_lat REAL,
                location_lon REAL,
                timestamp TEXT NOT NULL,
                card_type TEXT,
                payment_method TEXT,
                hour INTEGER,
                day_of_week INTEGER,
                is_weekend BOOLEAN,
                previous_transaction_minutes INTEGER,
                account_balance REAL,
                is_fraud BOOLEAN,
                fraud_score REAL,
                confidence TEXT,
                anomaly_score REAL,
                processed_at TEXT,
                processing_time_ms INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


@contextmanager
def get_db():
    """Database context manager"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


# Pydantic models
class Location(BaseModel):
    city: str
    country: str
    lat: float
    lon: float


class FraudPrediction(BaseModel):
    is_fraud: bool
    fraud_score: float
    confidence: str
    anomaly_score: Optional[float] = None


class Transaction(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    merchant_id: str
    merchant_category: str
    location: Location
    timestamp: str
    card_type: str
    payment_method: str
    hour: int
    day_of_week: int
    is_weekend: bool
    previous_transaction_minutes: int
    account_balance: float
    fraud_prediction: FraudPrediction
    processed_at: str
    processing_time_ms: int


class TransactionSummary(BaseModel):
    total_transactions: int
    fraud_transactions: int
    fraud_rate: float
    total_amount: float
    fraud_amount: float
    avg_processing_time: float


# Initialize database on startup
init_database()


@app.get("/")
async def root():
    return {"message": "Fraud Detection API", "status": "running"}


@app.post("/api/transactions")
async def create_transaction(transaction: Transaction):
    """Receive processed transaction from Kafka consumer"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO transactions (
                    transaction_id, user_id, amount, merchant_id, merchant_category,
                    location_city, location_country, location_lat, location_lon,
                    timestamp, card_type, payment_method, hour, day_of_week,
                    is_weekend, previous_transaction_minutes, account_balance,
                    is_fraud, fraud_score, confidence, anomaly_score,
                    processed_at, processing_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction.transaction_id,
                transaction.user_id,
                transaction.amount,
                transaction.merchant_id,
                transaction.merchant_category,
                transaction.location.city,
                transaction.location.country,
                transaction.location.lat,
                transaction.location.lon,
                transaction.timestamp,
                transaction.card_type,
                transaction.payment_method,
                transaction.hour,
                transaction.day_of_week,
                transaction.is_weekend,
                transaction.previous_transaction_minutes,
                transaction.account_balance,
                transaction.fraud_prediction.is_fraud,
                transaction.fraud_prediction.fraud_score,
                transaction.fraud_prediction.confidence,
                transaction.fraud_prediction.anomaly_score,
                transaction.processed_at,
                transaction.processing_time_ms
            ))
            conn.commit()

        return {"status": "success", "transaction_id": transaction.transaction_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/transactions", response_model=List[Dict[str, Any]])
async def get_transactions(
        limit: int = 100,
        offset: int = 0,
        fraud_only: Optional[bool] = None,
        merchant_category: Optional[str] = None
):
    """Get transactions with optional filters"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Build query with filters
            query = "SELECT * FROM transactions WHERE 1=1"
            params = []

            if fraud_only is not None:
                query += " AND is_fraud = ?"
                params.append(fraud_only)

            if merchant_category:
                query += " AND merchant_category = ?"
                params.append(merchant_category)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            transactions = []
            for row in rows:
                transaction = dict(row)
                # Convert timestamp strings back to proper format
                transaction['location'] = {
                    'city': transaction.pop('location_city'),
                    'country': transaction.pop('location_country'),
                    'lat': transaction.pop('location_lat'),
                    'lon': transaction.pop('location_lon')
                }
                transaction['fraud_prediction'] = {
                    'is_fraud': transaction.pop('is_fraud'),
                    'fraud_score': transaction.pop('fraud_score'),
                    'confidence': transaction.pop('confidence'),
                    'anomaly_score': transaction.pop('anomaly_score')
                }
                transactions.append(transaction)

            return transactions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/transactions/summary", response_model=TransactionSummary)
async def get_transactions_summary():
    """Get transaction summary statistics"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Get overall statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_transactions,
                    SUM(amount) as total_amount,
                    SUM(CASE WHEN is_fraud THEN amount ELSE 0 END) as fraud_amount,
                    AVG(processing_time_ms) as avg_processing_time
                FROM transactions
            """)

            row = cursor.fetchone()

            total_transactions = row[0] or 0
            fraud_transactions = row[1] or 0
            total_amount = row[2] or 0.0
            fraud_amount = row[3] or 0.0
            avg_processing_time = row[4] or 0.0

            fraud_rate = (fraud_transactions / total_transactions * 100) if total_transactions > 0 else 0.0

            return TransactionSummary(
                total_transactions=total_transactions,
                fraud_transactions=fraud_transactions,
                fraud_rate=round(fraud_rate, 2),
                total_amount=round(total_amount, 2),
                fraud_amount=round(fraud_amount, 2),
                avg_processing_time=round(avg_processing_time, 2)
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/transactions/stats")
async def get_transaction_stats():
    """Get detailed statistics for dashboard"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Fraud by merchant category
            cursor.execute("""
                SELECT 
                    merchant_category,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
                    ROUND(AVG(CASE WHEN is_fraud THEN 1.0 ELSE 0.0 END) * 100, 2) as fraud_rate
                FROM transactions 
                GROUP BY merchant_category
                ORDER BY fraud_rate DESC
            """)
            fraud_by_category = [dict(row) for row in cursor.fetchall()]

            # Hourly transaction pattern
            cursor.execute("""
                SELECT 
                    hour,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count
                FROM transactions 
                GROUP BY hour
                ORDER BY hour
            """)
            hourly_pattern = [dict(row) for row in cursor.fetchall()]

            # Recent transactions trend (last 24 hours simulation)
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count
                FROM transactions 
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            daily_trend = [dict(row) for row in cursor.fetchall()]

            return {
                "fraud_by_category": fraud_by_category,
                "hourly_pattern": hourly_pattern,
                "daily_trend": daily_trend
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    # Run the FastAPI server
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )