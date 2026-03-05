"""
Flask UI for Kafka DLQ Monitoring Dashboard
Provides a web interface for visualizing and monitoring error messages.
"""

import json
import logging
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configuration
API_BASE_URL = "http://localhost:8000"
REFRESH_INTERVAL = 5000  # milliseconds


# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kafka DLQ Error Monitoring</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .status-bar {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 20px;
            background: #f5f5f5;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        
        .status-label {
            color: #666;
            font-size: 0.9em;
        }
        
        .status-value {
            color: #333;
            font-weight: bold;
            font-size: 1.2em;
        }
        
        .status-item.healthy {
            border-left-color: #10b981;
        }
        
        .status-item.unhealthy {
            border-left-color: #ef4444;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .stat-box {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .severity-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            margin: 2px;
        }
        
        .severity-info {
            background: #dbeafe;
            color: #1e40af;
        }
        
        .severity-warning {
            background: #fef3c7;
            color: #92400e;
        }
        
        .severity-error {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .severity-critical {
            background: #fecaca;
            color: #7f1d1d;
        }
        
        .error-list {
            max-height: 500px;
            overflow-y: auto;
        }
        
        .error-item {
            padding: 15px;
            border: 1px solid #e5e7eb;
            border-radius: 5px;
            margin-bottom: 10px;
            background: #f9fafb;
            transition: all 0.3s ease;
        }
        
        .error-item:hover {
            background: #f3f4f6;
            border-color: #667eea;
            box-shadow: 0 2px 4px rgba(102, 126, 234, 0.1);
        }
        
        .error-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }
        
        .error-service {
            font-weight: bold;
            color: #667eea;
            font-size: 0.95em;
        }
        
        .error-time {
            color: #999;
            font-size: 0.85em;
        }
        
        .error-message {
            color: #333;
            margin: 8px 0;
            font-size: 0.95em;
        }
        
        .error-payload {
            background: white;
            padding: 10px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.8em;
            color: #666;
            margin-top: 8px;
            max-height: 150px;
            overflow-y: auto;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-size: 0.95em;
            transition: all 0.3s ease;
        }
        
        button:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button.secondary {
            background: #6b7280;
        }
        
        button.secondary:hover {
            background: #4b5563;
        }
        
        .loading {
            text-align: center;
            color: #999;
            padding: 20px;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .chart-container {
            margin-top: 20px;
            padding: 20px;
            background: #f9fafb;
            border-radius: 8px;
        }
        
        .chart-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
            font-size: 1.1em;
        }
        
        .chart-bar {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .chart-label {
            width: 120px;
            color: #666;
            font-size: 0.9em;
        }
        
        .chart-bar-fill {
            flex: 1;
            height: 25px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 3px;
            margin: 0 10px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 10px;
            color: white;
            font-size: 0.85em;
            font-weight: bold;
        }
        
        .chart-value {
            width: 40px;
            text-align: right;
            color: #333;
            font-weight: bold;
        }
        
        .error-count {
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
            text-align: center;
            margin: 20px 0;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            h1 {
                font-size: 1.8em;
            }
            
            .status-bar {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Kafka DLQ Error Monitoring</h1>
            <div class="status-bar">
                <div class="status-item" id="health-status">
                    <span class="status-label">System Status:</span>
                    <span class="status-value">Checking...</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Last Updated:</span>
                    <span class="status-value" id="last-updated">--:--:--</span>
                </div>
            </div>
        </header>
        
        <div class="grid">
            <!-- Error Count Card -->
            <div class="card">
                <h2>Total Errors</h2>
                <div class="error-count" id="total-errors">0</div>
                <div class="controls">
                    <button onclick="refreshData()">🔄 Refresh</button>
                    <button class="secondary" onclick="clearErrors()">🗑️ Clear</button>
                </div>
            </div>
            
            <!-- Severity Distribution Card -->
            <div class="card">
                <h2>By Severity</h2>
                <div class="chart-container" id="severity-chart"></div>
            </div>
            
            <!-- Service Distribution Card -->
            <div class="card">
                <h2>By Service</h2>
                <div class="chart-container" id="service-chart"></div>
            </div>
        </div>
        
        <!-- Recent Errors Card -->
        <div class="card">
            <h2>Recent Errors</h2>
            <div class="controls">
                <button onclick="loadMoreErrors()">📥 Load More</button>
            </div>
            <div class="error-list" id="error-list">
                <div class="loading">
                    <span class="spinner"></span>
                    Loading errors...
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const API_BASE_URL = "{{ api_url }}";
        const REFRESH_INTERVAL = {{ refresh_interval }};
        let currentLimit = 10;
        
        async function fetchData(endpoint) {
            try {
                const response = await fetch(`${API_BASE_URL}${endpoint}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return await response.json();
            } catch (error) {
                console.error('Fetch error:', error);
                return null;
            }
        }
        
        async function checkHealth() {
            const data = await fetchData('/health');
            const statusElement = document.getElementById('health-status');
            
            if (data) {
                const isHealthy = data.status === 'healthy' && data.consumer_running;
                statusElement.className = `status-item ${isHealthy ? 'healthy' : 'unhealthy'}`;
                statusElement.innerHTML = `
                    <span class="status-label">System Status:</span>
                    <span class="status-value">${isHealthy ? '✅ Healthy' : '⚠️ Degraded'}</span>
                `;
            } else {
                statusElement.className = 'status-item unhealthy';
                statusElement.innerHTML = `
                    <span class="status-label">System Status:</span>
                    <span class="status-value">❌ Offline</span>
                `;
            }
        }
        
        async function loadErrorCount() {
            const data = await fetchData('/errors/count');
            if (data) {
                document.getElementById('total-errors').textContent = data.count;
            }
        }
        
        async function loadErrorStats() {
            const data = await fetchData('/errors/stats');
            if (!data) return;
            
            // Severity chart
            const severityChart = document.getElementById('severity-chart');
            if (data.by_severity && Object.keys(data.by_severity).length > 0) {
                const maxSeverity = Math.max(...Object.values(data.by_severity));
                severityChart.innerHTML = `
                    <div class="chart-title">Error Distribution by Severity</div>
                    ${Object.entries(data.by_severity).map(([severity, count]) => `
                        <div class="chart-bar">
                            <div class="chart-label">${severity}</div>
                            <div class="chart-bar-fill" style="width: ${(count / maxSeverity * 100)}%">
                                ${count}
                            </div>
                            <div class="chart-value">${count}</div>
                        </div>
                    `).join('')}
                `;
            } else {
                severityChart.innerHTML = '<div class="loading">No data available</div>';
            }
            
            // Service chart
            const serviceChart = document.getElementById('service-chart');
            if (data.by_service && Object.keys(data.by_service).length > 0) {
                const maxService = Math.max(...Object.values(data.by_service));
                serviceChart.innerHTML = `
                    <div class="chart-title">Error Distribution by Service</div>
                    ${Object.entries(data.by_service).map(([service, count]) => `
                        <div class="chart-bar">
                            <div class="chart-label">${service}</div>
                            <div class="chart-bar-fill" style="width: ${(count / maxService * 100)}%">
                                ${count}
                            </div>
                            <div class="chart-value">${count}</div>
                        </div>
                    `).join('')}
                `;
            } else {
                serviceChart.innerHTML = '<div class="loading">No data available</div>';
            }
        }
        
        function getSeverityClass(severity) {
            const severityMap = {
                'INFO': 'severity-info',
                'WARNING': 'severity-warning',
                'ERROR': 'severity-error',
                'CRITICAL': 'severity-critical'
            };
            return severityMap[severity] || 'severity-error';
        }
        
        async function loadErrors() {
            const data = await fetchData(`/errors/details?limit=${currentLimit}`);
            if (!data || !data.errors) {
                document.getElementById('error-list').innerHTML = '<div class="loading">No errors found</div>';
                return;
            }
            
            const errorList = document.getElementById('error-list');
            if (data.errors.length === 0) {
                errorList.innerHTML = '<div class="loading">No errors captured yet</div>';
                return;
            }
            
            errorList.innerHTML = data.errors.map(error => `
                <div class="error-item">
                    <div class="error-header">
                        <span class="error-service">${error.source_service}</span>
                        <span class="severity-badge ${getSeverityClass(error.severity)}">
                            ${error.severity}
                        </span>
                        <span class="error-time">${new Date(error.timestamp).toLocaleString()}</span>
                    </div>
                    <div class="error-message">${error.error_message}</div>
                    ${Object.keys(error.payload).length > 0 ? `
                        <div class="error-payload">${JSON.stringify(error.payload, null, 2)}</div>
                    ` : ''}
                </div>
            `).join('');
        }
        
        function updateTimestamp() {
            const now = new Date();
            document.getElementById('last-updated').textContent = now.toLocaleTimeString();
        }
        
        async function refreshData() {
            updateTimestamp();
            await checkHealth();
            await loadErrorCount();
            await loadErrorStats();
            await loadErrors();
        }
        
        function loadMoreErrors() {
            currentLimit += 10;
            loadErrors();
        }
        
        async function clearErrors() {
            if (confirm('Are you sure you want to clear all errors? This action cannot be undone.')) {
                try {
                    const response = await fetch(`${API_BASE_URL}/errors/clear`, {
                        method: 'POST'
                    });
                    if (response.ok) {
                        alert('All errors cleared successfully');
                        currentLimit = 10;
                        await refreshData();
                    }
                } catch (error) {
                    console.error('Error clearing errors:', error);
                    alert('Failed to clear errors');
                }
            }
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh
        setInterval(refreshData, REFRESH_INTERVAL);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Render the main dashboard."""
    return render_template_string(
        HTML_TEMPLATE,
        api_url=API_BASE_URL,
        refresh_interval=REFRESH_INTERVAL
    )


@app.route("/api/health")
def health():
    """Health check endpoint."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return jsonify({"status": "ok", "backend": response.status_code == 200})
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "backend": False}), 500


if __name__ == "__main__":
    logger.info(f"Starting Flask UI on http://0.0.0.0:5000")
    logger.info(f"Backend API: {API_BASE_URL}")
    app.run(host="0.0.0.0", port=5000, debug=False)
