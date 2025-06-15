import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, BarChart, Bar
} from 'recharts';
import {
  Database, RefreshCw, Plus, Trash2, Clock,
  TrendingUp, AlertCircle
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
      const txRes = await fetch(`${API_BASE_URL}/api/transactions?page=${page}&size=20`);
      const sumRes = await fetch(`${API_BASE_URL}/api/transactions/summary`);

      if (!txRes.ok || !sumRes.ok) throw new Error('Failed to fetch data');

      const txData = await txRes.json();
      const sumData = await sumRes.json();

      setTransactions(txData.items || []);
      setTotalPages(txData.pages || 1);
      setSummary(sumData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const addTransaction = async () => {
    try {
      const data = JSON.parse(newTransaction);
      const res = await fetch(`${API_BASE_URL}/api/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setNewTransaction('{}');
      setShowAddForm(false);
      fetchData();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const deleteTransaction = async (id) => {
    await fetch(`${API_BASE_URL}/api/transactions/${id}`, { method: 'DELETE' });
    fetchData();
  };

  const clearAllTransactions = async () => {
    if (window.confirm('Clear all?')) {
      await fetch(`${API_BASE_URL}/api/transactions`, { method: 'DELETE' });
      fetchData();
    }
  };

  useEffect(() => { fetchData(); }, [page]);
  useEffect(() => {
    if (autoRefresh) {
      const i = setInterval(fetchData, 5000);
      return () => clearInterval(i);
    }
  }, [autoRefresh, page]);

  const getHourlyData = () => {
    const hourly = Array(24).fill(0);
    transactions.forEach(t => {
      const h = new Date(t.received_at).getHours();
      hourly[h]++;
    });
    return hourly.map((c, h) => ({ hour: `${h}:00`, transactions: c }));
  };

  if (loading && !transactions.length) {
    return <div className="text-white h-screen flex items-center justify-center"><RefreshCw className="animate-spin" /><p>Loading...</p></div>;
  }

  if (error) {
    return <div className="text-white h-screen flex items-center justify-center">
      <AlertCircle className="text-red-500" />
      <p>Error: {error}</p>
    </div>;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Transaction Dashboard</h1>
        <div className="space-x-2">
          <button onClick={() => setShowAddForm(!showAddForm)} className="bg-green-600 px-4 py-2 rounded">+ Add</button>
          <button onClick={clearAllTransactions} className="bg-red-600 px-4 py-2 rounded">Clear All</button>
          <button onClick={fetchData} className="bg-blue-600 px-4 py-2 rounded">Refresh</button>
        </div>
      </div>

      {showAddForm && (
        <div className="mb-4 bg-gray-800 p-4 rounded">
          <textarea value={newTransaction} onChange={(e) => setNewTransaction(e.target.value)}
            className="w-full bg-gray-700 p-2 rounded text-sm text-white" rows={5} />
          <button onClick={addTransaction} className="mt-2 bg-green-500 px-4 py-1 rounded">Submit</button>
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="bg-gray-800 p-4 rounded">Total: {summary.total_transactions}</div>
          <div className="bg-gray-800 p-4 rounded">Latest: {summary.latest_transaction}</div>
          <div className="bg-gray-800 p-4 rounded">Oldest: {summary.oldest_transaction}</div>
        </div>
      )}

      <div className="mb-4 bg-gray-800 p-4 rounded">
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

      <div className="overflow-x-auto bg-gray-800 p-4 rounded">
        <table className="table-auto w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="px-2 py-2 text-left">ID</th>
              <th className="px-2 py-2 text-left">Time</th>
              <th className="px-2 py-2 text-left">Details</th>
              <th className="px-2 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map(t => (
              <tr key={t.transaction_id} className={`border-b border-gray-700 ${t.data.prediction === 1 ? 'bg-red-900/40' : ''}`}>
                <td className="px-2 py-2 font-mono text-xs">{t.transaction_id}</td>
                <td className="px-2 py-2">{new Date(t.received_at).toLocaleString()}</td>
                <td className="px-2 py-2 text-xs">
                  <div><strong>Pred:</strong> {t.data.prediction ?? 'N/A'}</div>
                  <div><strong>Prob:</strong> {t.data.fraud_probability?.toFixed(3) ?? 'N/A'}</div>
                  <div><strong>User:</strong> {t.data.user_id ?? 'N/A'}</div>
                  <div><strong>Amt:</strong> {t.data.amount ?? 'N/A'}</div>
                </td>
                <td className="px-2 py-2">
                  <button onClick={() => deleteTransaction(t.transaction_id)} className="bg-red-600 px-2 py-1 rounded">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 flex justify-between items-center">
          <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} className="px-3 py-1 bg-gray-600 rounded">Prev</button>
          <span>Page {page} / {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} className="px-3 py-1 bg-gray-600 rounded">Next</button>
        </div>
      </div>
    </div>
  );
};

export default TransactionDashboard;
