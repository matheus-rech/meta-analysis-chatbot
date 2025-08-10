"""
Health check and monitoring utilities for Meta-Analysis Chatbot
"""

import os
import psutil
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.checks_performed = 0
        self.last_check = None
        self.status_history = []
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'status': 'ok' if cpu_percent < 80 else 'warning' if cpu_percent < 95 else 'critical'
                },
                'memory': {
                    'percent': memory.percent,
                    'available_gb': memory.available / (1024**3),
                    'status': 'ok' if memory.percent < 80 else 'warning' if memory.percent < 95 else 'critical'
                },
                'disk': {
                    'percent': disk.percent,
                    'free_gb': disk.free / (1024**3),
                    'status': 'ok' if disk.percent < 80 else 'warning' if disk.percent < 95 else 'critical'
                }
            }
        except Exception as e:
            logger.error(f"Failed to check system resources: {e}")
            return {'error': str(e)}
    
    def check_r_backend(self) -> Dict[str, Any]:
        """Check if R backend is available"""
        try:
            result = subprocess.run(
                ['Rscript', '-e', 'cat("OK")'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            r_available = result.returncode == 0 and "OK" in result.stdout
            
            # Check required packages
            packages_check = subprocess.run(
                ['Rscript', '-e', 'all(c("meta", "metafor", "jsonlite") %in% installed.packages()[,"Package"])'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            packages_installed = "TRUE" in packages_check.stdout
            
            return {
                'available': r_available,
                'packages_installed': packages_installed,
                'version': self._get_r_version() if r_available else None,
                'status': 'ok' if r_available and packages_installed else 'error'
            }
        except subprocess.TimeoutExpired:
            return {'available': False, 'status': 'timeout', 'error': 'R backend timeout'}
        except Exception as e:
            return {'available': False, 'status': 'error', 'error': str(e)}
    
    def _get_r_version(self) -> str:
        """Get R version"""
        try:
            result = subprocess.run(
                ['Rscript', '--version'],
                capture_output=True,
                text=True,
                timeout=2
            )
            # Parse version from stderr (where R outputs version info)
            if result.stderr:
                lines = result.stderr.split('\n')
                for line in lines:
                    if 'version' in line.lower():
                        return line.strip()
            return "Unknown"
        except:
            return "Unknown"
    
    def check_api_keys(self) -> Dict[str, Any]:
        """Check API key configuration"""
        return {
            'openai': {
                'configured': bool(os.getenv('OPENAI_API_KEY')),
                'status': 'ok' if os.getenv('OPENAI_API_KEY') else 'warning'
            },
            'anthropic': {
                'configured': bool(os.getenv('ANTHROPIC_API_KEY')),
                'status': 'ok' if os.getenv('ANTHROPIC_API_KEY') else 'warning'
            },
            'any_configured': bool(os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'))
        }
    
    def check_directories(self) -> Dict[str, Any]:
        """Check required directories"""
        dirs = {
            'sessions': Path(os.getenv('SESSIONS_DIR', './sessions')),
            'outputs': Path('./outputs'),
            'logs': Path('./logs'),
            'cache': Path('./cache')
        }
        
        status = {}
        for name, path in dirs.items():
            exists = path.exists()
            writable = os.access(path, os.W_OK) if exists else False
            
            # Try to create if doesn't exist
            if not exists:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    exists = True
                    writable = True
                except:
                    pass
            
            status[name] = {
                'path': str(path),
                'exists': exists,
                'writable': writable,
                'status': 'ok' if exists and writable else 'error'
            }
        
        return status
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check Python dependencies"""
        required_packages = [
            'gradio',
            'pandas',
            'numpy',
            'langchain',
            'pydantic',
            'pytz',
            'PIL',
            'PyPDF2'
        ]
        
        status = {}
        for package in required_packages:
            try:
                __import__(package)
                status[package] = {'installed': True, 'status': 'ok'}
            except ImportError:
                status[package] = {'installed': False, 'status': 'error'}
        
        all_installed = all(p['installed'] for p in status.values())
        return {
            'packages': status,
            'all_installed': all_installed,
            'status': 'ok' if all_installed else 'error'
        }
    
    def get_full_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        self.checks_performed += 1
        self.last_check = datetime.now()
        
        health_status = {
            'timestamp': self.last_check.isoformat(),
            'checks_performed': self.checks_performed,
            'system': self.check_system_resources(),
            'r_backend': self.check_r_backend(),
            'api_keys': self.check_api_keys(),
            'directories': self.check_directories(),
            'dependencies': self.check_dependencies()
        }
        
        # Calculate overall status
        statuses = []
        for component in ['system', 'r_backend', 'directories', 'dependencies']:
            if component in health_status:
                comp_status = health_status[component].get('status')
                if comp_status:
                    statuses.append(comp_status)
        
        if 'error' in statuses or 'critical' in statuses:
            overall_status = 'unhealthy'
        elif 'warning' in statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        health_status['overall_status'] = overall_status
        
        # Keep history (last 10 checks)
        self.status_history.append({
            'timestamp': self.last_check.isoformat(),
            'status': overall_status
        })
        self.status_history = self.status_history[-10:]
        health_status['history'] = self.status_history
        
        return health_status
    
    def get_simple_health_check(self) -> Dict[str, Any]:
        """Simple health check for load balancers"""
        try:
            # Quick checks only
            r_check = subprocess.run(
                ['Rscript', '-e', 'cat("OK")'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            r_ok = r_check.returncode == 0
            api_ok = bool(os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'))
            
            healthy = r_ok and api_ok
            
            return {
                'status': 'healthy' if healthy else 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'checks': {
                    'r_backend': r_ok,
                    'api_keys': api_ok
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

# Create FastAPI health endpoint
def create_health_endpoint(app):
    """Add health check endpoints to FastAPI app"""
    from fastapi import FastAPI, Response
    import json
    
    health_checker = HealthChecker()
    
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint"""
        result = health_checker.get_simple_health_check()
        status_code = 200 if result['status'] == 'healthy' else 503
        return Response(
            content=json.dumps(result),
            media_type="application/json",
            status_code=status_code
        )
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with all components"""
        result = health_checker.get_full_health_status()
        status_code = 200 if result['overall_status'] == 'healthy' else 503 if result['overall_status'] == 'unhealthy' else 200
        return Response(
            content=json.dumps(result, default=str),
            media_type="application/json",
            status_code=status_code
        )
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus-compatible metrics endpoint"""
        metrics_data = []
        
        # System metrics
        resources = health_checker.check_system_resources()
        if 'cpu' in resources:
            metrics_data.append(f"cpu_usage_percent {resources['cpu']['percent']}")
        if 'memory' in resources:
            metrics_data.append(f"memory_usage_percent {resources['memory']['percent']}")
            metrics_data.append(f"memory_available_gb {resources['memory']['available_gb']}")
        if 'disk' in resources:
            metrics_data.append(f"disk_usage_percent {resources['disk']['percent']}")
            metrics_data.append(f"disk_free_gb {resources['disk']['free_gb']}")
        
        # Application metrics
        metrics_data.append(f"health_checks_total {health_checker.checks_performed}")
        
        return Response(
            content="\n".join(metrics_data),
            media_type="text/plain"
        )
    
    return app

# Standalone health check script
if __name__ == "__main__":
    import sys
    
    checker = HealthChecker()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--detailed":
        result = checker.get_full_health_status()
    else:
        result = checker.get_simple_health_check()
    
    print(json.dumps(result, indent=2, default=str))
    
    # Exit with appropriate code
    if result.get('status') == 'healthy' or result.get('overall_status') == 'healthy':
        sys.exit(0)
    else:
        sys.exit(1)