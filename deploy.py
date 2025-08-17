#!/usr/bin/env python3
"""
Production Deployment Script for Meta-Analysis Chatbot
Implements monitoring and security features
"""
import os
import json
import time
# import subprocess
import threading
from pathlib import Path
from datetime import datetime


class ProductionMonitor:
    """Production monitoring and management system"""
    
    def __init__(self):
        self.repo_root = Path(__file__).parent
        self.config_dir = self.repo_root / "config"
        self.logs_dir = self.repo_root / "logs"
        self.metrics_dir = self.repo_root / "metrics"
        
        # Create directories
        for directory in [self.config_dir, self.logs_dir, self.metrics_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        self.running = False
        self.monitoring_thread = None
        
    def load_config(self):
        """Load monitoring configuration"""
        config_file = self.config_dir / "monitoring.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
"""Load monitoring configuration"""
        config_file = self.config_dir / "monitoring.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except (PermissionError, OSError):
                # Log the error
                self.log_message('ERROR', f"Failed to read config file: {config_file}")
                return self.get_default_config()
        else:
            return self.get_default_config()
            
    def get_default_config(self):
        """Return default configuration"""
        return {
            'performance': {
                'enabled': True,
                'interval_seconds': 300,
                'cpu_threshold': 80,
                'memory_threshold': 80
            },
            'security': {
                'enabled': True,
                'rate_limit_per_minute': 30,
                'session_timeout_hours': 24
            },
            'logging': {
                'level': 'INFO',
                'file': str(self.logs_dir / 'production.log'),
                'max_size_mb': 100
            }
        }
        else:
            # Default configuration
            return {
                'performance': {
                    'enabled': True,
                    'interval_seconds': 300,
                    'cpu_threshold': 80,
                    'memory_threshold': 80
                },
                'security': {
                    'enabled': True,
                    'rate_limit_per_minute': 30,
                    'session_timeout_hours': 24
                },
                'logging': {
                    'level': 'INFO',
                    'file': str(self.logs_dir / 'production.log'),
                    'max_size_mb': 100
                }
            }
            
    def log_message(self, level, message):
        """Log message with timestamp"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        
        # Write to log file
        log_file = self.logs_dir / "production.log"
        with open(log_file, 'a') as f:
            f.write(log_entry + '\n')
            
    def collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # Try to use psutil if available
            import psutil
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': {
                    'percent': psutil.virtual_memory().percent,
                    'used_gb': psutil.virtual_memory().used / (1024**3),
                    'total_gb': psutil.virtual_memory().total / (1024**3)
                },
                'disk': {
                    'percent': psutil.disk_usage('/').percent,
                    'used_gb': psutil.disk_usage('/').used / (1024**3),
                    'free_gb': psutil.disk_usage('/').free / (1024**3)
                },
                'process_count': len(psutil.pids())
            }
            
        except ImportError:
            # Fallback to basic system commands
            try:
                # Get load average
                load_result = subprocess.run(['uptime'], capture_output=True, text=True)
                load_avg = load_result.stdout.strip() if load_result.returncode == 0 else "unknown"
                
                # Get memory info
                mem_result = subprocess.run(['free', '-m'], capture_output=True, text=True)
                mem_info = mem_result.stdout.strip() if mem_result.returncode == 0 else "unknown"
                
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'load_average': load_avg,
                    'memory_info': mem_info,
                    'method': 'system_commands'
                }
                
            except Exception as e:
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e),
                    'method': 'error_fallback'
                }
                
        return metrics
        
    def check_r_health(self):
        """Check R backend health"""
        try:
            result = subprocess.run(['/usr/bin/Rscript', '-e', 'library(jsonlite); cat(toJSON(list(status="healthy")))'], capture_output=True, text=True, timeout=10)
                            result = subprocess.run(['Rscript', '-e', 'library(jsonlite); cat(toJSON(list(status="healthy")))'], capture_output=True, text=True, timeout=10)
                capture_output=True, text=True, timeout=10
def check_r_health(self):
        """Check R backend health"""
        try:
            result = subprocess.run(['Rscript', '-e', 'library(jsonlite); cat(toJSON(list(status="healthy")))'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return {'status': 'healthy', 'response_time': 'fast'}
            
            if result.returncode == 0:
                return {'status': 'healthy', 'response_time': 'fast'}
            else:
                return {'status': 'error', 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'error': 'R script timeout'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
            
    def check_session_health(self):
        """Check session management health"""
        sessions_dir = self.repo_root / "sessions"
        if not sessions_dir.exists():
            return {'status': 'error', 'error': 'sessions directory missing'}
            
        try:
            # Count active sessions
            session_count = len([d for d in sessions_dir.iterdir() if d.is_dir()])
            
            # Check for old sessions (older than 24 hours)
            old_sessions = []
            current_time = time.time()
            
            for session_dir in sessions_dir.iterdir():
                if session_dir.is_dir():
                    session_time = session_dir.stat().st_mtime
                    age_hours = (current_time - session_time) / 3600
                    if age_hours > 24:
                        old_sessions.append(session_dir.name)
                        
            return {
                'status': 'healthy',
                'active_sessions': session_count,
                'old_sessions': len(old_sessions),
                'old_session_list': old_sessions[:5]  # Show first 5
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
            
    def cleanup_old_sessions(self):
        """Clean up old sessions"""
        sessions_dir = self.repo_root / "sessions"
        if not sessions_dir.exists():
            return
            
        current_time = time.time()
        cleanup_count = 0
        
        for session_dir in sessions_dir.iterdir():
            if session_dir.is_dir():
                session_time = session_dir.stat().st_mtime
                age_hours = (current_time - session_time) / 3600
                
                # Remove sessions older than 48 hours
                if age_hours > 48:
                    try:
                        import shutil
                        shutil.rmtree(session_dir)
                        cleanup_count += 1
                        self.log_message('INFO', f"Cleaned up old session: {session_dir.name}")
                    except Exception as e:
                        self.log_message('ERROR', f"Failed to cleanup session {session_dir.name}: {e}")
                        
        if cleanup_count > 0:
            self.log_message('INFO', f"Cleaned up {cleanup_count} old sessions")
            
    def perform_health_check(self):
        """Perform comprehensive health check"""
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': self.collect_system_metrics(),
            'r_backend': self.check_r_health(),
            'session_management': self.check_session_health(),
            'overall_status': 'healthy'
        }
        
        # Determine overall status
        if health_data['r_backend']['status'] != 'healthy':
            health_data['overall_status'] = 'degraded'
            
        if health_data['session_management']['status'] != 'healthy':
            health_data['overall_status'] = 'degraded'
            
        # Check system thresholds
        try:
            cpu = health_data['system_metrics'].get('cpu_percent', 0)
            memory = health_data['system_metrics'].get('memory', {}).get('percent', 0)
            
            if cpu > 90 or memory > 90:
                health_data['overall_status'] = 'critical'
            elif cpu > 80 or memory > 80:
                health_data['overall_status'] = 'warning'
                
        except (KeyError, TypeError):
            pass  # Ignore errors in threshold checking
            
        # Save health check results
        health_file = self.metrics_dir / f"health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(health_file, 'w') as f:
            json.dump(health_data, f, indent=2)
            
        # Keep only recent health checks (last 24 hours)
        self.cleanup_old_health_checks()
        
        return health_data
        
    def cleanup_old_health_checks(self):
        """Remove old health check files"""
        current_time = time.time()
        
        for health_file in self.metrics_dir.glob("health_*.json"):
            file_time = health_file.stat().st_mtime
            age_hours = (current_time - file_time) / 3600
            
            if age_hours > 24:
                try:
                    health_file.unlink()
                except:
                    pass
                    
    def monitoring_loop(self):
        """Main monitoring loop"""
        config = self.load_config()
        interval = config.get('performance', {}).get('interval_seconds', 300)
        
        self.log_message('INFO', 'Monitoring system started')
        
        while self.running:
            try:
                # Perform health check
                health_data = self.perform_health_check()
                
                # Log status
                status = health_data['overall_status']
                self.log_message('INFO', f"Health check completed - Status: {status}")
                
                # Alert on issues
                if status in ['critical', 'warning']:
                    self.log_message('ALERT', f"System status: {status}")
                    
                # Cleanup old sessions periodically
                if time.time() % 3600 < interval:  # Once per hour
                    self.cleanup_old_sessions()
                # Cleanup old sessions once per hour
                now = time.time()
                # Cleanup old sessions once per hour
                now = time.time()
                if now - self.last_cleanup_time >= 3600:
                    self.cleanup_old_sessions()
                    self.last_cleanup_time = now
                
                # Wait for next check
                time.sleep(interval)
                
            except Exception as e:
                self.log_message('ERROR', f"Monitoring error: {e}")
                time.sleep(60)  # Short sleep on error
                
        self.log_message('INFO', 'Monitoring system stopped')
        
    def start_monitoring(self):
        """Start monitoring in background thread"""
        if not self.running:
            self.running = True
            self.monitoring_thread = threading.Thread(target=self.monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            self.log_message('INFO', 'Background monitoring started')
            
    def stop_monitoring(self):
        """Stop monitoring"""
        if self.running:
            self.running = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=10)
            self.log_message('INFO', 'Monitoring stopped')
            
    def get_status_summary(self):
        """Get current status summary"""
        health_data = self.perform_health_check()
        
        summary = {
            'status': health_data['overall_status'],
            'timestamp': health_data['timestamp'],
            'r_backend': health_data['r_backend']['status'],
            'sessions': health_data['session_management'].get('active_sessions', 0)
        }
        
        # Add system metrics if available
        if 'cpu_percent' in health_data['system_metrics']:
            summary['cpu'] = f"{health_data['system_metrics']['cpu_percent']:.1f}%"
            summary['memory'] = f"{health_data['system_metrics']['memory']['percent']:.1f}%"
            
        return summary


class DeploymentManager:
    """Manage deployment and startup"""
    
    def __init__(self):
        self.repo_root = Path(__file__).parent
        self.monitor = ProductionMonitor()
        
    def check_prerequisites(self):
        """Check deployment prerequisites"""
        print("Checking deployment prerequisites...")
        
        checks = {
            'r_available': False,
            'api_keys': False,
            'directories': False,
            'config_files': False
        }
        
        # Check R
        try:
            subprocess.run(['R', '--version'], capture_output=True, check=True)
            checks['r_available'] = True
            print("✓ R is available")
        except:
            print("✗ R not available")
            
        # Check API keys
        if os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'):
            checks['api_keys'] = True
            print("✓ API keys configured")
        else:
            print("⚠ No API keys found (set OPENAI_API_KEY or ANTHROPIC_API_KEY)")
            
        # Check directories
        required_dirs = ['sessions', 'logs', 'config']
        all_dirs_exist = True
        for dirname in required_dirs:
            dirpath = self.repo_root / dirname
            if dirpath.exists():
                print(f"✓ Directory exists: {dirname}")
            else:
                print(f"✗ Missing directory: {dirname}")
                all_dirs_exist = False
        checks['directories'] = all_dirs_exist
        
        # Check config files
        env_file = self.repo_root / ".env"
        if env_file.exists():
            checks['config_files'] = True
            print("✓ Configuration file (.env) exists")
        else:
            print("⚠ No .env file found")
            
        return checks
        
# Import session management library
# from flask import session  # Assuming Flask is used for session management

def start_application(self, mode='production'):
    """Start the application"""
    print(f"
Starting application in {mode} mode...")
    
    # Start monitoring
    self.monitor.start_monitoring()
    
    # Verify user role from server-side session data
    if self.verify_user_role('admin'):  # Implement this method to check server-side session
        if mode == 'production':
            # Start the main chatbot application
            chatbot_script = self.repo_root / "chatbot_langchain.py"
            if chatbot_script.exists():
                print(f"Starting main application: {chatbot_script}")
                print("Application would start here (in actual deployment)")
                print("Access at: http://localhost:7860")
            else:
                print("⚠ Main application script not found")
                
        elif mode == 'docker':
            print("For Docker deployment, run:")
            print("  docker build -f Dockerfile.chatbot -t meta-analysis-chatbot .")
            print("  docker run -p 7860:7860 -e OPENAI_API_KEY=\"your-key\" meta-analysis-chatbot")
    else:
        print("Unauthorized access. Please login with appropriate credentials.")
        
    return True
        """Start the application"""
        print(f"\nStarting application in {mode} mode...")
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        if mode == 'production':
            # Start the main chatbot application
            chatbot_script = self.repo_root / "chatbot_langchain.py"
            if chatbot_script.exists():
                print(f"Starting main application: {chatbot_script}")
                print("Application would start here (in actual deployment)")
                print("Access at: http://localhost:7860")
            else:
                print("⚠ Main application script not found")
                
        elif mode == 'docker':
            print("For Docker deployment, run:")
            print("  docker build -f Dockerfile.chatbot -t meta-analysis-chatbot .")
            print("  docker run -p 7860:7860 -e OPENAI_API_KEY=\"your-key\" meta-analysis-chatbot")
            
        return True
        
    def show_status(self):
        """Show current status"""
        print("\n" + "="*60)
        print("  PRODUCTION STATUS")
        print("="*60)
        
        status = self.monitor.get_status_summary()
        
        print(f"Overall Status: {status['status'].upper()}")
        print(f"Timestamp: {status['timestamp']}")
        print(f"R Backend: {status['r_backend']}")
        print(f"Active Sessions: {status['sessions']}")
        
        if 'cpu' in status:
            print(f"CPU Usage: {status['cpu']}")
            print(f"Memory Usage: {status['memory']}")
            
        print("\nFor detailed metrics, check:")
        print(f"  Logs: {self.monitor.logs_dir}")
        print(f"  Metrics: {self.monitor.metrics_dir}")
        

def main():
    """Main deployment script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Meta-Analysis Chatbot Deployment')
    parser.add_argument('action', choices=['setup', 'start', 'status', 'monitor'], 
                       help='Action to perform')
    parser.add_argument('--mode', choices=['development', 'production', 'docker'],
                       default='production', help='Deployment mode')
    
    args = parser.parse_args()
    
    manager = DeploymentManager()
    
    if args.action == 'setup':
        print("Setting up deployment environment...")
        checks = manager.check_prerequisites()
        
        if all(checks.values()):
            print("\n✓ All prerequisites met - ready for deployment")
        else:
            print("\n⚠ Some prerequisites missing - check above")
            
    elif args.action == 'start':
        checks = manager.check_prerequisites()
        if checks['r_available'] and checks['directories']:
            manager.start_application(args.mode)
            
            # Keep running to show monitoring
            try:
                print("\nPress Ctrl+C to stop...")
                while True:
elif args.action == 'start':
        checks = manager.check_prerequisites()
        if checks['r_available'] and checks['directories']:
            manager.start_application(args.mode)
            
            # Keep running to show monitoring
            try:
                print("
Press Ctrl+C to stop...")
                stop_event = threading.Event()
                while not stop_event.is_set():
                    status = manager.monitor.get_status_summary()
                    print(f"Status: {status['status']} | R: {status['r_backend']} | Sessions: {status['sessions']}")
                    stop_event.wait(10)
                    
            except KeyboardInterrupt:
                print("
Shutting down...")
                manager.monitor.stop_monitoring()
        else:
            print("Cannot start - prerequisites not met")
            
    elif args.action == 'status':
        manager.show_status()
        
    elif args.action == 'monitor':
        manager.monitor.start_monitoring()
        try:
            print("Monitoring running... Press Ctrl+C to stop")
            stop_event = threading.Event()
            while not stop_event.is_set():
                status = manager.monitor.get_status_summary()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status['status']} | R: {status['r_backend']} | Sessions: {status['sessions']}")
                stop_event.wait(5)
        except KeyboardInterrupt:
            manager.monitor.stop_monitoring()
                    status = manager.monitor.get_status_summary()
                    print(f"Status: {status['status']} | R: {status['r_backend']} | Sessions: {status['sessions']}")
                    
            except KeyboardInterrupt:
                print("\nShutting down...")
                manager.monitor.stop_monitoring()
        else:
            print("Cannot start - prerequisites not met")
            
    elif args.action == 'status':
        manager.show_status()
        
    elif args.action == 'monitor':
        manager.monitor.start_monitoring()
        try:
            print("Monitoring running... Press Ctrl+C to stop")
            while True:
                time.sleep(5)
                status = manager.monitor.get_status_summary()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status['status']} | R: {status['r_backend']} | Sessions: {status['sessions']}")
        except KeyboardInterrupt:
            manager.monitor.stop_monitoring()


if __name__ == "__main__":
    main()