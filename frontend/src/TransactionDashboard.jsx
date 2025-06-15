import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import {
  Database,
  RefreshCw,
  Plus,
  Trash2,
  Clock,
  TrendingUp,
  AlertCircle,
} from 'lucide-react';

const API_BASE_URL = 'http://54.251.172.36:8000';

const TransactionDashboard = () => {
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTransaction, setNewTransaction] = useState('{}');

  const fetchData = async () => {
    try {
      setLoading(true);

      const transactionsRes = await fetch(`${API_BASE_URL}/api/transactions?page=${page}&size=20`);
      const transactionsData = await transactionsRes.json();

      const summaryRes = await fetch(`${API_BASE_URL}/api/transactions/summary`);
      const summaryData = await summaryRes.json();

      setTransactions(transactionsData.items);
      setTotalPages(transactionsData.pages);
      setSummary(summaryData);
    } catch (err) {
      console.error(err);
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const addTransaction = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: newTransaction,
      });

      if (!response.ok) throw new Error('Failed to add transaction');
      setNewTransaction('{}');
      setShowAddForm(false);
      fetchData();
    } catch (err) {
      alert(err.message);
    }
  };

  const deleteTransaction = async (id) => {
    try {
      await fetch(`${API_BASE_URL}/api/transactions/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (err) {
      alert('Error deleting transaction');
    }
  };

  const clearAllTransactions = async () => {
    if (!window.confirm('Clear all transactions?')) return;
    try {
      await fetch(`${API_BASE_URL}/api/transactions`, { method: 'DELETE' });
      fetchData();
    } catch (err) {
      alert('Error clearing transactions');
    }
  };

  useEffect(() => {
    fetchData();
  }, [page]);

  useEffect(() => {
    let interval;
    if (autoRefresh) interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, page]);

  const getHourlyData = () => {
    const hourlyCount = new Array(24).fill(0);
    transactions.forEach((tx) => {
      const hour = new Date(tx.received_at).getHours();
      hourlyCount[hour]++;
    });
    return hourlyCount.map((count, hour) => ({ hour: `${hour}:00`, transactions: count }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <Database className="text-blue-500" />
          <h1 className="text-xl font-bold">Transaction Dashboard</h1>
        </div>
        <div className="flex gap-2">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            Auto-refresh
          </label>
          <button onClick={() => setShowAddForm(!showAddForm)} className="bg-green-600 px-3 py-1 rounded flex items-center gap-1">
            <Plus size={16} /> Add
          </button>
          <button onClick={clearAllTransactions} className="bg-red-600 px-3 py-1 rounded flex items-center gap-1">
            <Trash2 size={16} /> Clear All
          </button>
          <button onClick={fetchData} className="bg-blue-600 px-3 py-1 rounded flex items-center gap-1">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      </header>

      <main className="p-6">
        {showAddForm && (
          <div className="bg-gray-800 p-4 rounded mb-6">
            <textarea value={newTransaction} onChange={(e) => setNewTransaction(e.target.value)} className="w-full h-32 bg-gray-700 text-sm font-mono p-2 rounded" />
            <div className="flex gap-2 mt-2">
              <button onClick={addTransaction} className="bg-green-600 px-4 py-1 rounded">Add</button>
              <button onClick={() => setShowAddForm(false)} className="bg-gray-600 px-4 py-1 rounded">Cancel</button>
            </div>
          </div>
        )}

        {summary && (
          <div className="grid md:grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-800 p-4 rounded">
              <p className="text-sm text-gray-400">Total Transactions</p>
              <p className="text-xl font-bold">{summary.total_transactions}</p>
            </div>
            <div className="bg-gray-800 p-4 rounded">
              <p className="text-sm text-gray-400">Latest Transaction</p>
              <p className="text-lg">{new Date(summary.latest_transaction).toLocaleString()}</p>
            </div>
            <div className="bg-gray-800 p-4 rounded">
              <p className="text-sm text-gray-400">Oldest Transaction</p>
              <p className="text-lg">{new Date(summary.oldest_transaction).toLocaleString()}</p>
            </div>
          </div>
        )}

        <div className="bg-gray-800 p-4 rounded mb-6">
          <h2 className="text-lg font-semibold mb-4">Hourly Transaction Pattern</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={getHourlyData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" stroke="#ccc" />
              <YAxis stroke="#ccc" />
              <Tooltip />
              <Bar dataKey="transactions" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-800 p-4 rounded">
          <div className="flex justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Transactions</h2>
            <div>
              Page {page} of {totalPages}
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="ml-2">Prev</button>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="ml-2">Next</button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Received At</th>
                  <th>Data</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.transaction_id}>
                    <td>{tx.transaction_id}</td>
                    <td>{new Date(tx.received_at).toLocaleString()}</td>
                    <td><pre className="text-xs bg-gray-900 p-1 rounded max-w-md truncate">{JSON.stringify(tx.data)}</pre></td>
                    <td><button onClick={() => deleteTransaction(tx.transaction_id)} className="bg-red-600 px-2 py-1 text-xs rounded">Delete</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
};

export default TransactionDashboard;
