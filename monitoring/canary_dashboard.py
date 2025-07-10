#!/usr/bin/env python3
"""
Canary Dashboard - Web interface for monitoring synthetic canary workflows
=========================================================================

This module provides a web dashboard for visualizing canary workflow results,
system health status, and performance metrics.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from synthetic_canary_workflows import CanaryOrchestrator, CanaryStatus

logger = logging.getLogger(__name__)

app = FastAPI(title="Canary Monitoring Dashboard", version="1.0.0")

# Global orchestrator instance
orchestrator = None


def load_canary_results(hours: int = 24) -> List[Dict[str, Any]]:
    """Load canary results from the last N hours"""
    results_dir = Path("monitoring/canary_results")
    
    if not results_dir.exists():
        return []
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    results = []
    
    for results_file in results_dir.glob("canary_results_*.json"):
        try:
            with open(results_file, 'r') as f:
                file_results = json.load(f)
                
                # Filter by time
                for result in file_results:
                    if result.get('start_time', 0) > cutoff_time.timestamp():
                        results.append(result)
                        
        except Exception as e:
            logger.error(f"Error loading results from {results_file}: {e}")
    
    return sorted(results, key=lambda x: x.get('start_time', 0), reverse=True)


@app.get("/")
async def dashboard_home(request: Request):
    """Main dashboard page"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Canary Monitoring Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric-value { font-size: 2em; font-weight: bold; margin-bottom: 10px; }
            .metric-label { color: #666; font-size: 0.9em; }
            .healthy { color: #4CAF50; }
            .warning { color: #FF9800; }
            .critical { color: #F44336; }
            .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .results-table { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f8f9fa; font-weight: 600; }
            .status-success { background: #d4edda; color: #155724; padding: 4px 8px; border-radius: 4px; }
            .status-failure { background: #f8d7da; color: #721c24; padding: 4px 8px; border-radius: 4px; }
            .status-error { background: #f8d7da; color: #721c24; padding: 4px 8px; border-radius: 4px; }
            .status-timeout { background: #fff3cd; color: #856404; padding: 4px 8px; border-radius: 4px; }
            .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
            .refresh-btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🕊️ Canary Monitoring Dashboard</h1>
                <p>Real-time monitoring of synthetic canary workflows</p>
                <button class="refresh-btn" onclick="refreshDashboard()">Refresh Data</button>
                <button class="refresh-btn" onclick="runCanaries()">Run Canaries Now</button>
            </div>
            
            <div class="metrics" id="metrics">
                <!-- Metrics will be loaded here -->
            </div>
            
            <div class="chart-container">
                <h3>Success Rate Over Time</h3>
                <canvas id="successChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>Response Time Trends</h3>
                <canvas id="responseTimeChart"></canvas>
            </div>
            
            <div class="results-table">
                <h3>Recent Canary Results</h3>
                <table id="resultsTable">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Workflow</th>
                            <th>Status</th>
                            <th>Response Time</th>
                            <th>Error</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Results will be loaded here -->
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            let successChart, responseTimeChart;
            
            function refreshDashboard() {
                loadMetrics();
                loadCharts();
                loadResults();
            }
            
            function loadMetrics() {
                fetch('/api/metrics')
                    .then(response => response.json())
                    .then(data => {
                        const metricsDiv = document.getElementById('metrics');
                        metricsDiv.innerHTML = `
                            <div class="metric-card">
                                <div class="metric-value ${data.overall_health.status === 'healthy' ? 'healthy' : data.overall_health.status === 'degraded' ? 'warning' : 'critical'}">
                                    ${data.overall_health.status.toUpperCase()}
                                </div>
                                <div class="metric-label">System Health</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">${Math.round(data.overall_health.success_rate * 100)}%</div>
                                <div class="metric-label">Success Rate (24h)</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">${data.total_executions}</div>
                                <div class="metric-label">Total Executions</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">${data.avg_response_time}ms</div>
                                <div class="metric-label">Avg Response Time</div>
                            </div>
                        `;
                    });
            }
            
            function loadCharts() {
                fetch('/api/charts')
                    .then(response => response.json())
                    .then(data => {
                        // Success rate chart
                        if (successChart) successChart.destroy();
                        const ctx1 = document.getElementById('successChart').getContext('2d');
                        successChart = new Chart(ctx1, {
                            type: 'line',
                            data: {
                                labels: data.timestamps,
                                datasets: [{
                                    label: 'Success Rate %',
                                    data: data.success_rates,
                                    borderColor: '#4CAF50',
                                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                                    tension: 0.1
                                }]
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        max: 100
                                    }
                                }
                            }
                        });
                        
                        // Response time chart
                        if (responseTimeChart) responseTimeChart.destroy();
                        const ctx2 = document.getElementById('responseTimeChart').getContext('2d');
                        responseTimeChart = new Chart(ctx2, {
                            type: 'line',
                            data: {
                                labels: data.timestamps,
                                datasets: [{
                                    label: 'Response Time (ms)',
                                    data: data.response_times,
                                    borderColor: '#2196F3',
                                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                                    tension: 0.1
                                }]
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    y: {
                                        beginAtZero: true
                                    }
                                }
                            }
                        });
                    });
            }
            
            function loadResults() {
                fetch('/api/results')
                    .then(response => response.json())
                    .then(data => {
                        const tbody = document.querySelector('#resultsTable tbody');
                        tbody.innerHTML = data.map(result => `
                            <tr>
                                <td>${new Date(result.start_time * 1000).toLocaleString()}</td>
                                <td>${result.workflow_id}</td>
                                <td><span class="status-${result.status}">${result.status.toUpperCase()}</span></td>
                                <td>${result.response_time ? Math.round(result.response_time * 1000) + 'ms' : 'N/A'}</td>
                                <td>${result.error_message || ''}</td>
                            </tr>
                        `).join('');
                    });
            }
            
            function runCanaries() {
                fetch('/api/run-canaries', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        alert('Canaries executed. Check results in a few moments.');
                        setTimeout(refreshDashboard, 5000);
                    });
            }
            
            // Initial load
            refreshDashboard();
            
            // Auto-refresh every 30 seconds
            setInterval(refreshDashboard, 30000);
        </script>
    </body>
    </html>
    """)


@app.get("/api/metrics")
async def get_metrics():
    """Get system health metrics"""
    results = load_canary_results(24)  # Last 24 hours
    
    if not results:
        return {
            "overall_health": {"status": "unknown", "success_rate": 0},
            "total_executions": 0,
            "avg_response_time": 0
        }
    
    # Calculate metrics
    total_executions = len(results)
    successful_executions = sum(1 for r in results if r.get('status') == 'success')
    success_rate = successful_executions / total_executions if total_executions > 0 else 0
    
    # Calculate average response time
    response_times = [r.get('response_time', 0) for r in results if r.get('response_time')]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Determine overall health
    if success_rate >= 0.95:
        health_status = "healthy"
    elif success_rate >= 0.80:
        health_status = "degraded"
    else:
        health_status = "critical"
    
    return {
        "overall_health": {
            "status": health_status,
            "success_rate": success_rate
        },
        "total_executions": total_executions,
        "avg_response_time": round(avg_response_time * 1000)  # Convert to ms
    }


@app.get("/api/charts")
async def get_chart_data():
    """Get data for charts"""
    results = load_canary_results(24)  # Last 24 hours
    
    if not results:
        return {
            "timestamps": [],
            "success_rates": [],
            "response_times": []
        }
    
    # Group results by hour
    hourly_data = {}
    
    for result in results:
        timestamp = result.get('start_time', 0)
        hour_key = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:00')
        
        if hour_key not in hourly_data:
            hourly_data[hour_key] = []
        
        hourly_data[hour_key].append(result)
    
    # Calculate hourly metrics
    timestamps = []
    success_rates = []
    response_times = []
    
    for hour_key in sorted(hourly_data.keys()):
        hour_results = hourly_data[hour_key]
        
        # Success rate for this hour
        successful = sum(1 for r in hour_results if r.get('status') == 'success')
        success_rate = (successful / len(hour_results)) * 100 if hour_results else 0
        
        # Average response time for this hour
        hour_response_times = [r.get('response_time', 0) for r in hour_results if r.get('response_time')]
        avg_response_time = sum(hour_response_times) / len(hour_response_times) if hour_response_times else 0
        
        timestamps.append(hour_key)
        success_rates.append(success_rate)
        response_times.append(avg_response_time * 1000)  # Convert to ms
    
    return {
        "timestamps": timestamps,
        "success_rates": success_rates,
        "response_times": response_times
    }


@app.get("/api/results")
async def get_results():
    """Get recent canary results"""
    results = load_canary_results(24)  # Last 24 hours
    
    # Return most recent 50 results
    return results[:50]


@app.post("/api/run-canaries")
async def run_canaries():
    """Trigger canary execution"""
    global orchestrator
    
    if not orchestrator:
        orchestrator = CanaryOrchestrator()
    
    try:
        # Run canaries in background
        asyncio.create_task(orchestrator.run_all_canaries())
        
        return {"status": "started", "message": "Canary execution started"}
    except Exception as e:
        logger.error(f"Failed to run canaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    global orchestrator
    
    if not orchestrator:
        orchestrator = CanaryOrchestrator()
    
    health_status = orchestrator.get_health_status()
    
    return {
        "status": "ok",
        "canary_health": health_status,
        "timestamp": datetime.now().isoformat()
    }


def main():
    """Main entry point for canary dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run canary monitoring dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for canaries")
    parser.add_argument("--token", help="Authentication token")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize orchestrator
    global orchestrator
    orchestrator = CanaryOrchestrator(args.url, args.token)
    
    # Run dashboard
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()