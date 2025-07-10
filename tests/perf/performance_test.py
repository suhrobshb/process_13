#!/usr/bin/env python3
"""
Performance Test Runner
=====================

Automated performance testing script that runs various load testing scenarios
and generates comprehensive performance reports.
"""

import os
import sys
import time
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import requests


class PerformanceTestRunner:
    """Orchestrates performance testing with multiple scenarios"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results_dir = Path("tests/perf/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Test scenarios
        self.scenarios = {
            "smoke": {
                "description": "Quick smoke test with minimal load",
                "users": 10,
                "spawn_rate": 2,
                "run_time": "2m",
                "expected_failure_rate": 0.01
            },
            "normal": {
                "description": "Normal operational load",
                "users": 100,
                "spawn_rate": 10,
                "run_time": "10m",
                "expected_failure_rate": 0.05
            },
            "peak": {
                "description": "Peak usage simulation",
                "users": 500,
                "spawn_rate": 25,
                "run_time": "15m",
                "expected_failure_rate": 0.1
            },
            "stress": {
                "description": "Stress test with 1000+ concurrent users",
                "users": 1000,
                "spawn_rate": 50,
                "run_time": "20m",
                "expected_failure_rate": 0.15
            },
            "spike": {
                "description": "Spike load test",
                "users": 2000,
                "spawn_rate": 100,
                "run_time": "5m",
                "expected_failure_rate": 0.2
            }
        }
    
    def health_check(self) -> bool:
        """Verify the system is healthy before testing"""
        print("🔍 Performing health check...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=30)
            if response.status_code == 200:
                print("✅ Health check passed")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def run_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Run a specific performance test scenario"""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        scenario = self.scenarios[scenario_name]
        print(f"🚀 Running {scenario_name} scenario: {scenario['description']}")
        
        # Prepare results file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"{scenario_name}_{timestamp}.json"
        
        # Build locust command
        locust_cmd = [
            "locust",
            "-f", "tests/perf/locustfile.py",
            "--headless",
            "-u", str(scenario["users"]),
            "-r", str(scenario["spawn_rate"]),
            "-t", scenario["run_time"],
            "--host", self.base_url,
            "--json", str(results_file)
        ]
        
        print(f"📊 Command: {' '.join(locust_cmd)}")
        
        # Run locust
        start_time = time.time()
        try:
            result = subprocess.run(locust_cmd, capture_output=True, text=True, timeout=1800)
            end_time = time.time()
            
            # Parse results
            test_results = {
                "scenario": scenario_name,
                "config": scenario,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            # Load detailed results if available
            if results_file.exists():
                with open(results_file, 'r') as f:
                    detailed_results = json.load(f)
                    test_results["detailed_results"] = detailed_results
            
            # Analyze results
            test_results["analysis"] = self.analyze_results(test_results)
            
            return test_results
            
        except subprocess.TimeoutExpired:
            print(f"❌ Test timed out after 30 minutes")
            return {"error": "timeout", "scenario": scenario_name}
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return {"error": str(e), "scenario": scenario_name}
    
    def analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance test results"""
        analysis = {
            "overall_status": "unknown",
            "performance_metrics": {},
            "issues": [],
            "recommendations": []
        }
        
        # Analyze exit code
        if results.get("exit_code") == 0:
            analysis["overall_status"] = "passed"
        else:
            analysis["overall_status"] = "failed"
            analysis["issues"].append(f"Non-zero exit code: {results.get('exit_code')}")
        
        # Analyze stdout for key metrics
        stdout = results.get("stdout", "")
        if stdout:
            # Extract key metrics from Locust output
            lines = stdout.split('\n')
            for line in lines:
                if "requests/s" in line and "failures/s" in line:
                    # Parse summary line
                    parts = line.split()
                    if len(parts) >= 8:
                        analysis["performance_metrics"]["requests_per_second"] = float(parts[5])
                        analysis["performance_metrics"]["failures_per_second"] = float(parts[7])
                
                if "50%" in line and "90%" in line:
                    # Parse percentile line
                    parts = line.split()
                    if len(parts) >= 6:
                        analysis["performance_metrics"]["median_response_time"] = float(parts[1])
                        analysis["performance_metrics"]["p90_response_time"] = float(parts[3])
        
        # Check failure rate
        failure_rate = analysis["performance_metrics"].get("failures_per_second", 0)
        request_rate = analysis["performance_metrics"].get("requests_per_second", 1)
        
        if request_rate > 0:
            failure_percentage = (failure_rate / request_rate) * 100
            analysis["performance_metrics"]["failure_percentage"] = failure_percentage
            
            scenario_config = results.get("config", {})
            expected_failure_rate = scenario_config.get("expected_failure_rate", 0.1) * 100
            
            if failure_percentage > expected_failure_rate:
                analysis["issues"].append(f"High failure rate: {failure_percentage:.2f}% (expected < {expected_failure_rate:.2f}%)")
        
        # Check response times
        p90_response = analysis["performance_metrics"].get("p90_response_time", 0)
        if p90_response > 5000:  # 5 seconds
            analysis["issues"].append(f"High P90 response time: {p90_response}ms")
            analysis["recommendations"].append("Consider optimizing slow endpoints")
        
        # Generate recommendations
        if analysis["issues"]:
            analysis["recommendations"].extend([
                "Check application logs for errors",
                "Monitor database performance",
                "Review resource utilization (CPU, memory)",
                "Consider horizontal scaling if needed"
            ])
        
        return analysis
    
    def generate_report(self, all_results: List[Dict[str, Any]]) -> str:
        """Generate comprehensive performance test report"""
        report = ["# Performance Test Report", ""]
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Base URL:** {self.base_url}")
        report.append("")
        
        # Summary table
        report.append("## Test Summary")
        report.append("")
        report.append("| Scenario | Status | Users | Duration | Req/s | Failure Rate | P90 Response |")
        report.append("|----------|--------|--------|----------|--------|--------------|--------------|")
        
        for result in all_results:
            if "error" in result:
                report.append(f"| {result['scenario']} | ERROR | - | - | - | - | - |")
                continue
            
            analysis = result.get("analysis", {})
            metrics = analysis.get("performance_metrics", {})
            
            scenario = result["scenario"]
            status = analysis.get("overall_status", "unknown")
            users = result.get("config", {}).get("users", "-")
            duration = f"{result.get('duration', 0):.1f}s"
            req_per_s = metrics.get("requests_per_second", 0)
            failure_rate = f"{metrics.get('failure_percentage', 0):.2f}%"
            p90_response = f"{metrics.get('p90_response_time', 0):.0f}ms"
            
            report.append(f"| {scenario} | {status} | {users} | {duration} | {req_per_s:.1f} | {failure_rate} | {p90_response} |")
        
        report.append("")
        
        # Detailed results
        report.append("## Detailed Results")
        report.append("")
        
        for result in all_results:
            if "error" in result:
                report.append(f"### {result['scenario']} - ERROR")
                report.append(f"Error: {result['error']}")
                report.append("")
                continue
            
            scenario = result["scenario"]
            config = result.get("config", {})
            analysis = result.get("analysis", {})
            
            report.append(f"### {scenario}")
            report.append(f"**Description:** {config.get('description', 'N/A')}")
            report.append(f"**Configuration:** {config.get('users')} users, {config.get('spawn_rate')} spawn rate, {config.get('run_time')} duration")
            report.append(f"**Status:** {analysis.get('overall_status', 'unknown')}")
            report.append("")
            
            # Performance metrics
            metrics = analysis.get("performance_metrics", {})
            if metrics:
                report.append("**Performance Metrics:**")
                for key, value in metrics.items():
                    report.append(f"- {key.replace('_', ' ').title()}: {value}")
                report.append("")
            
            # Issues
            issues = analysis.get("issues", [])
            if issues:
                report.append("**Issues Found:**")
                for issue in issues:
                    report.append(f"- {issue}")
                report.append("")
            
            # Recommendations
            recommendations = analysis.get("recommendations", [])
            if recommendations:
                report.append("**Recommendations:**")
                for rec in recommendations:
                    report.append(f"- {rec}")
                report.append("")
        
        return "\n".join(report)
    
    def run_all_scenarios(self, scenarios: List[str] = None) -> List[Dict[str, Any]]:
        """Run all or specified scenarios"""
        if scenarios is None:
            scenarios = ["smoke", "normal", "peak", "stress"]
        
        all_results = []
        
        for scenario in scenarios:
            if scenario not in self.scenarios:
                print(f"⚠️  Unknown scenario: {scenario}")
                continue
            
            print(f"\n{'='*60}")
            print(f"Running scenario: {scenario}")
            print(f"{'='*60}")
            
            result = self.run_scenario(scenario)
            all_results.append(result)
            
            # Brief summary
            if "error" in result:
                print(f"❌ {scenario} failed: {result['error']}")
            else:
                analysis = result.get("analysis", {})
                status = analysis.get("overall_status", "unknown")
                metrics = analysis.get("performance_metrics", {})
                
                print(f"✅ {scenario} completed: {status}")
                if metrics:
                    print(f"   - Requests/s: {metrics.get('requests_per_second', 0):.1f}")
                    print(f"   - Failure rate: {metrics.get('failure_percentage', 0):.2f}%")
                    print(f"   - P90 response: {metrics.get('p90_response_time', 0):.0f}ms")
            
            # Brief pause between scenarios
            time.sleep(5)
        
        return all_results


def main():
    """Main entry point for performance testing"""
    parser = argparse.ArgumentParser(description="Run performance tests")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for testing")
    parser.add_argument("--scenarios", nargs="+", help="Specific scenarios to run")
    parser.add_argument("--no-health-check", action="store_true", help="Skip health check")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing results")
    
    args = parser.parse_args()
    
    runner = PerformanceTestRunner(args.url)
    
    if args.report_only:
        # Generate report from existing results
        results_dir = Path("tests/perf/results")
        if not results_dir.exists():
            print("❌ No results directory found")
            return 1
        
        print("📊 Generating report from existing results...")
        # This would need to be implemented to read existing results
        return 0
    
    # Health check
    if not args.no_health_check:
        if not runner.health_check():
            print("❌ Health check failed. Aborting tests.")
            return 1
    
    # Run scenarios
    print("🚀 Starting performance tests...")
    
    results = runner.run_all_scenarios(args.scenarios)
    
    # Generate report
    print("\n📊 Generating performance report...")
    report = runner.generate_report(results)
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = runner.results_dir / f"performance_report_{timestamp}.md"
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"📄 Report saved to: {report_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results if r.get("analysis", {}).get("overall_status") == "passed")
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All performance tests passed!")
        return 0
    else:
        print("❌ Some performance tests failed. Check the report for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())