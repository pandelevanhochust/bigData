# === BACKEND UPDATE ===
# File: backend/main.py

import sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import os

DB_PATH = "transactions.db"
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

# Models
class TransactionCreate(BaseModel):
    class Config:
        extra = "allow"

class Transaction(BaseModel):
    transaction_id: str
    received_at: str
    data: Dict[str, Any]

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


# === SQLite Helper Functions ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            received_at TEXT,
            data TEXT
        )
    ''')
    conn.commit()
    conn.close()


def insert_transaction(txn: Transaction):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO transactions (transaction_id, received_at, data)
                 VALUES (?, ?, ?)''',
              (txn.transaction_id, txn.received_at, json.dumps(txn.data)))
    conn.commit()
    conn.close()


def get_transactions(page: int, size: int) -> (List[Transaction], int):
    offset = (page - 1) * size
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions")
    total = c.fetchone()[0]
    c.execute("SELECT * FROM transactions ORDER BY received_at DESC LIMIT ? OFFSET ?", (size, offset))
    rows = c.fetchall()
    conn.close()
    items = [Transaction(transaction_id=r[0], received_at=r[1], data=json.loads(r[2])) for r in rows]
    return items, total


def delete_transaction_by_id(txn_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE transaction_id = ?", (txn_id,))
    conn.commit()
    conn.close()


def clear_transactions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()


def get_summary():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions")
    total = c.fetchone()[0]

    if total == 0:
        return TransactionSummary(total_transactions=0)

    c.execute("SELECT received_at FROM transactions ORDER BY received_at ASC LIMIT 1")
    oldest = c.fetchone()[0]
    c.execute("SELECT received_at FROM transactions ORDER BY received_at DESC LIMIT 1")
    latest = c.fetchone()[0]
    conn.close()
    return TransactionSummary(total_transactions=total, oldest_transaction=oldest, latest_transaction=latest)


@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/api/transactions", response_model=Transaction)
async def create_transaction(transaction_data: Dict[str, Any]):
    try:
        txn = Transaction(
            transaction_id=f"TXN_{uuid.uuid4().hex[:12].upper()}",
            received_at=datetime.now().isoformat(),
            data=transaction_data
        )
        insert_transaction(txn)
        return txn
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.get("/api/transactions", response_model=PaginatedResponse)
async def fetch_transactions(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)):
    items, total = get_transactions(page, size)
    return PaginatedResponse(
        items=items, total=total, page=page, size=size,
        pages=(total + size - 1) // size if total else 0
    )

@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str):
    delete_transaction_by_id(transaction_id)
    return {"status": "success"}

@app.delete("/api/transactions")
async def delete_all():
    clear_transactions()
    return {"status": "cleared"}

@app.get("/api/transactions/summary", response_model=TransactionSummary)
async def summary():
    return get_summary()

@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

