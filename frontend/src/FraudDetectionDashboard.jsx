import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { AlertTriangle, Shield, DollarSign, Clock, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000'; // Change to your EC2 FastAPI server URL

const FraudDetectionDashboard = () => {
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch data from API
  const fetchData = async () => {
    try {
      setLoading(true);

      // Fetch transactions
      const fraudParam = filter === 'fraud' ? 'true' : filter === 'normal' ? 'false' : '';
      const transactionsResponse = await fetch(`${API_BASE_URL}/api/transactions?limit=50${fraudParam ? `&fraud_only=${fraudParam}` : ''}`);
      const transactionsData = await transactionsResponse.json();

      // Fetch summary
      const summaryResponse = await fetch(`${API_BASE_URL}/api/transactions/summary`);
      const summaryData = await summaryResponse.json();

      // Fetch stats
      const statsResponse = await fetch(`${API_BASE_URL}/api/transactions/stats`);
      const statsData = await statsResponse.json();

      setTransactions(transactionsData);
      setSummary(summaryData);
      setStats(statsData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh functionality
  useEffect(() => {
    fetchData();

    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [filter, autoRefresh]);

  const COLORS = ['#ef4444', '#22c55e', '#3b82f6', '#f59e0b'];

  if (loading && !transactions.length) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center">
        <div className="text-center text-white">
          <RefreshCw className="animate-spin h-12 w-12 mx-auto mb-4" />
          <p className="text-xl">Loading fraud detection data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center">
        <div className="text-center text-white">
          <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-red-500" />
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
            <Shield className="h-8 w-8 text-blue-500" />
            <h1 className="text-2xl font-bold">Fraud Detection Dashboard</h1>
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
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-sm"
            >
              <option value="all">All Transactions</option>
              <option value="fraud">Fraud Only</option>
              <option value="normal">Normal Only</option>
            </select>
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
        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
                  <p className="text-gray-400 text-sm">Fraud Detected</p>
                  <p className="text-2xl font-bold text-red-500">{summary.fraud_transactions}</p>
                  <p className="text-sm text-gray-400">{summary.fraud_rate}% fraud rate</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-red-500" />
              </div>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Total Amount</p>
                  <p className="text-2xl font-bold">${summary.total_amount.toLocaleString()}</p>
                  <p className="text-sm text-red-400">${summary.fraud_amount.toLocaleString()} fraud</p>
                </div>
                <DollarSign className="h-8 w-8 text-green-500" />
              </div>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Avg Processing Time</p>
                  <p className="text-2xl font-bold">{summary.avg_processing_time}ms</p>
                </div>
                <Clock className="h-8 w-8 text-yellow-500" />
              </div>
            </div>
          </div>
        )}

        {/* Charts */}
        {stats && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Fraud by Category */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <BarChart className="h-5 w-5 mr-2" />
                Fraud by Merchant Category
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={stats.fraud_by_category}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="merchant_category" stroke="#9CA3AF" fontSize={12} />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    labelStyle={{ color: '#F3F4F6' }}
                  />
                  <Bar dataKey="fraud_rate" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Hourly Pattern */}
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <LineChart className="h-5 w-5 mr-2" />
                Hourly Transaction Pattern
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={stats.hourly_pattern}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="hour" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                    labelStyle={{ color: '#F3F4F6' }}
                  />
                  <Line type="monotone" dataKey="total" stroke="#3b82f6" strokeWidth={2} />
                  <Line type="monotone" dataKey="fraud_count" stroke="#ef4444" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Recent Transactions */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Transactions</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-2">Transaction ID</th>
                  <th className="text-left py-3 px-2">Amount</th>
                  <th className="text-left py-3 px-2">Merchant</th>
                  <th className="text-left py-3 px-2">Location</th>
                  <th className="text-left py-3 px-2">Status</th>
                  <th className="text-left py-3 px-2">Fraud Score</th>
                  <th className="text-left py-3 px-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((transaction) => (
                  <tr key={transaction.transaction_id} className="border-b border-gray-700 hover:bg-gray-700">
                    <td className="py-3 px-2 font-mono text-xs">
                      {transaction.transaction_id.substring(0, 8)}...
                    </td>
                    <td className="py-3 px-2 font-semibold">
                      ${transaction.amount.toFixed(2)}
                    </td>
                    <td className="py-3 px-2">{transaction.merchant_category}</td>
                    <td className="py-3 px-2">
                      {transaction.location.city}, {transaction.location.country}
                    </td>
                    <td className="py-3 px-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        transaction.fraud_prediction.is_fraud 
                          ? 'bg-red-900 text-red-300' 
                          : 'bg-green-900 text-green-300'
                      }`}>
                        {transaction.fraud_prediction.is_fraud ? 'FRAUD' : 'NORMAL'}
                      </span>
                    </td>
                    <td className="py-3 px-2">
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-700 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              transaction.fraud_prediction.fraud_score > 0.7 ? 'bg-red-500' :
                              transaction.fraud_prediction.fraud_score > 0.4 ? 'bg-yellow-500' : 'bg-green-500'
                            }`}
                            style={{ width: `${transaction.fraud_prediction.fraud_score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400">
                          {(transaction.fraud_prediction.fraud_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-2 text-gray-400 text-xs">
                      {new Date(transaction.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FraudDetectionDashboard;