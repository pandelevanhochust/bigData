from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uvicorn
import uuid

app = FastAPI(title="Transaction API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://54.251.172.36:3000",
        "http://localhost:5173",
        "http://54.251.172.36:3000",
        "http://localhost:3000",
        "https://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Flexible models to accept any data structure
class TransactionCreate(BaseModel):
    """Accept any transaction data"""

    class Config:
        extra = "allow"  # Allow additional fields


class Transaction(BaseModel):
    transaction_id: str
    received_at: str
    data: Dict[str, Any]  # Store all received data as-is

    class Config:
        extra = "allow"


class TransactionSummary(BaseModel):
    total_transactions: int
    latest_transaction: Optional[str] = None
    oldest_transaction: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[Transaction]
    total: int
    page: int
    size: int
    pages: int


# In-memory storage
transactions_db: List[Dict] = []


def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    return f"TXN_{uuid.uuid4().hex[:12].upper()}"


# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Transaction API",
        "status": "running",
        "version": "1.0.0",
        "description": "Accepts and stores any transaction data"
    }


@app.post("/api/transactions", response_model=Transaction)
async def create_transaction(transaction_data: Dict[str, Any]):
    """Accept any transaction data and store it"""
    try:
        transaction_id = generate_transaction_id()
        received_at = datetime.now().isoformat()

        transaction = Transaction(
            transaction_id=transaction_id,
            received_at=received_at,
            data=transaction_data
        )

        transactions_db.append(transaction.dict())

        return transaction
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing transaction: {str(e)}")


@app.get("/api/transactions", response_model=PaginatedResponse)
async def get_transactions(
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1, le=100)
):
    """Get all transactions with pagination"""

    total = len(transactions_db)
    start_idx = (page - 1) * size
    end_idx = start_idx + size

    paginated_transactions = transactions_db[start_idx:end_idx]

    return PaginatedResponse(
        items=[Transaction(**t) for t in paginated_transactions],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total > 0 else 0
    )


@app.get("/api/transactions/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str):
    """Get a specific transaction by ID"""
    transaction = next((t for t in transactions_db if t['transaction_id'] == transaction_id), None)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return Transaction(**transaction)


@app.get("/api/transactions/summary", response_model=TransactionSummary)
async def get_transactions_summary():
    """Get basic transaction statistics"""
    total = len(transactions_db)

    if total == 0:
        return TransactionSummary(
            total_transactions=0,
            latest_transaction=None,
            oldest_transaction=None
        )

    # Sort by received_at to get latest and oldest
    sorted_transactions = sorted(transactions_db, key=lambda x: x['received_at'])

    return TransactionSummary(
        total_transactions=total,
        latest_transaction=sorted_transactions[-1]['received_at'],
        oldest_transaction=sorted_transactions[0]['received_at']
    )


@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str):
    """Delete a specific transaction"""
    global transactions_db
    initial_length = len(transactions_db)
    transactions_db = [t for t in transactions_db if t['transaction_id'] != transaction_id]

    if len(transactions_db) == initial_length:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {"status": "success", "message": "Transaction deleted"}


@app.delete("/api/transactions")
async def clear_all_transactions():
    """Clear all transactions"""
    global transactions_db
    count = len(transactions_db)
    transactions_db.clear()
    return {"status": "success", "message": f"Cleared {count} transactions"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "transactions_count": len(transactions_db),
        "version": "1.0.0"
    }


# Catch-all endpoint to accept any POST request
@app.post("/api/webhook")
async def webhook_handler(data: Dict[str, Any]):
    """Generic webhook endpoint that accepts any data"""
    try:
        transaction_id = generate_transaction_id()
        received_at = datetime.now().isoformat()

        transaction = Transaction(
            transaction_id=transaction_id,
            received_at=received_at,
            data=data
        )

        transactions_db.append(transaction.dict())

        return {
            "status": "success",
            "transaction_id": transaction_id,
            "message": "Data received and stored"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing webhook: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )