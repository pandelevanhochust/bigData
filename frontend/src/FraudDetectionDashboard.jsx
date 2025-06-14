import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Database, RefreshCw, Plus, Trash2, Clock, TrendingUp, AlertCircle } from 'lucide-react';

const API_BASE_URL = 'https://54.251.172.36:8000'; // Change to your EC2 FastAPI server URL

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

  // Fetch data from API
  const fetchData = async () => {
    try {
      setLoading(true);

      // Fetch transactions with pagination
      const transactionsResponse = await fetch(`${API_BASE_URL}/api/transactions?page=${page}&size=20`);
      if (!transactionsResponse.ok) {
        throw new Error(`HTTP error! status: ${transactionsResponse.status}`);
      }
      const transactionsData = await transactionsResponse.json();

      // Fetch summary
      const summaryResponse = await fetch(`${API_BASE_URL}/api/transactions/summary`);
      if (!summaryResponse.ok) {
        throw new Error(`HTTP error! status: ${summaryResponse.status}`);
      }
      const summaryData = await summaryResponse.json();

      setTransactions(transactionsData.items || []);
      setTotalPages(transactionsData.pages || 1);
      setSummary(summaryData);
      setError(null);
    } catch (err) {
      console.error('Fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Add new transaction
  const addTransaction = async () => {
    try {
      const data = JSON.parse(newTransaction);
      const response = await fetch(`${API_BASE_URL}/api/transactions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setNewTransaction('{}');
      setShowAddForm(false);
      fetchData(); // Refresh data
    } catch (err) {
      alert(`Error adding transaction: ${err.message}`);
    }
  };

  // Delete transaction
  const deleteTransaction = async (transactionId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/transactions/${transactionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      fetchData(); // Refresh data
    } catch (err) {
      alert(`Error deleting transaction: ${err.message}`);
    }
  };

  // Clear all transactions
  const clearAllTransactions = async () => {
    if (window.confirm('Are you sure you want to clear all transactions?')) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/transactions`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        fetchData(); // Refresh data
      } catch (err) {
        alert(`Error clearing transactions: ${err.message}`);
      }
    }
  };

  // Auto-refresh functionality
  useEffect(() => {
    fetchData();
  }, [page]);

  useEffect(() => {
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, page]);

  // Create chart data from transactions
  const getHourlyData = () => {
    const hourlyCount = new Array(24).fill(0);
    transactions.forEach(transaction => {
      const hour = new Date(transaction.received_at).getHours();
      hourlyCount[hour]++;
    });

    return hourlyCount.map((count, hour) => ({
      hour: `${hour}:00`,
      transactions: count
    }));
  };

  if (loading && !transactions.length) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center">
        <div className="text-center text-white">
          <RefreshCw className="animate-spin h-12 w-12 mx-auto mb-4" />
          <p className="text-xl">Loading transaction data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center">
        <div className="text-center text-white">
          <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
          <p className="text-xl mb-4">Error loading data: {error}</p>
          <button
            onClick={fetchData}
            className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Database className="h-8 w-8 text-blue-500" />
            <h1 className="text-2xl font-bold">Transaction Dashboard</h1>
          </div>
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Auto-refresh</span>
            </label>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg transition-colors flex items-center space-x-2"
            >
              <Plus className="h-4 w-4" />
              <span>Add Transaction</span>
            </button>
            <button
              onClick={clearAllTransactions}
              className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg transition-colors flex items-center space-x-2"
            >
              <Trash2 className="h-4 w-4" />
              <span>Clear All</span>
            </button>
            <button
              onClick={fetchData}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg transition-colors flex items-center space-x-2"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Add Transaction Form */}
        {showAddForm && (
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Add New Transaction</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Transaction Data (JSON)</label>
                <textarea
                  value={newTransaction}
                  onChange={(e) => setNewTransaction(e.target.value)}
                  className="w-full h-32 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm font-mono"
                  placeholder='{"amount": 100, "user_id": "user123", "description": "Test transaction"}'
                />
              </div>
              <div className="flex space-x-4">
                <button
                  onClick={addTransaction}
                  className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded transition-colors"
                >
                  Add Transaction
                </button>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Total Transactions</p>
                  <p className="text-2xl font-bold">{summary.total_transactions.toLocaleString()}</p>
                </div>
                <TrendingUp className="h-8 w-8 text-blue-500" />
              </div>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Latest Transaction</p>
                  <p className="text-lg font-bold">
                    {summary.latest_transaction
                      ? new Date(summary.latest_transaction).toLocaleString()
                      : 'None'
                    }
                  </p>
                </div>
                <Clock className="h-8 w-8 text-green-500" />
              </div>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Oldest Transaction</p>
                  <p className="text-lg font-bold">
                    {summary.oldest_transaction
                      ? new Date(summary.oldest_transaction).toLocaleString()
                      : 'None'
                    }
                  </p>
                </div>
                <Database className="h-8 w-8 text-yellow-500" />
              </div>
            </div>
          </div>
        )}

        {/* Hourly Chart */}
        {transactions.length > 0 && (
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <LineChart className="h-5 w-5 mr-2" />
              Hourly Transaction Pattern
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={getHourlyData()}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="hour" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#F3F4F6' }}
                />
                <Bar dataKey="transactions" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Recent Transactions */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Recent Transactions</h3>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-400">
                Page {page} of {totalPages}
              </span>
              <div className="flex space-x-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  className="bg-gray-600 hover:bg-gray-700 disabled:opacity-50 px-3 py-1 rounded text-sm"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page >= totalPages}
                  className="bg-gray-600 hover:bg-gray-700 disabled:opacity-50 px-3 py-1 rounded text-sm"
                >
                  Next
                </button>
              </div>
            </div>
          </div>

          {transactions.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No transactions found</p>
              <p className="text-sm">Add some transactions to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-3 px-2">Transaction ID</th>
                    <th className="text-left py-3 px-2">Received At</th>
                    <th className="text-left py-3 px-2">Data Preview</th>
                    <th className="text-left py-3 px-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((transaction) => (
                    <tr key={transaction.transaction_id} className="border-b border-gray-700 hover:bg-gray-700">
                      <td className="py-3 px-2 font-mono text-xs">
                        {transaction.transaction_id}
                      </td>
                      <td className="py-3 px-2 text-gray-400">
                        {new Date(transaction.received_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-2">
                        <div className="max-w-md overflow-hidden">
                          <pre className="text-xs bg-gray-900 p-2 rounded truncate">
                            {JSON.stringify(transaction.data, null, 2).substring(0, 100)}
                            {JSON.stringify(transaction.data).length > 100 && '...'}
                          </pre>
                        </div>
                      </td>
                      <td className="py-3 px-2">
                        <button
                          onClick={() => deleteTransaction(transaction.transaction_id)}
                          className="bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-xs transition-colors"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TransactionDashboard;