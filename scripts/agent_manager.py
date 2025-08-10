#!/usr/bin/env python3
"""
Agent Manager for Meta-Analysis Chatbot
Manages background agents with enhanced capabilities
"""

import os
import sys
import json
import yaml
import asyncio
import threading
import subprocess
import multiprocessing
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging
import psutil
import signal

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for a background agent"""
    name: str
    type: str
    enabled: bool = True
    capabilities: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[Dict[str, Any]] = None
    

@dataclass
class AgentStatus:
    """Status of a running agent"""
    name: str
    pid: Optional[int] = None
    status: str = "idle"  # idle, running, failed, completed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class BackgroundAgent:
    """Base class for background agents"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = AgentStatus(name=config.name)
        self.process = None
        self.thread = None
        self.stop_event = threading.Event()
        
    async def start(self):
        """Start the agent"""
        self.status.status = "running"
        self.status.started_at = datetime.now()
        logger.info(f"Starting agent: {self.config.name}")
        
    async def stop(self):
        """Stop the agent"""
        self.stop_event.set()
        self.status.status = "idle"
        self.status.completed_at = datetime.now()
        logger.info(f"Stopping agent: {self.config.name}")
        
    async def execute(self, task: Dict[str, Any]) -> Any:
        """Execute a task"""
        raise NotImplementedError
        
    def get_status(self) -> AgentStatus:
        """Get current status"""
        return self.status


class StatisticalAnalysisAgent(BackgroundAgent):
    """Agent for statistical analysis tasks"""
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """Execute statistical analysis"""
        try:
            analysis_type = task.get("type", "meta_analysis")
            session_id = task.get("session_id")
            
            logger.info(f"Executing {analysis_type} for session {session_id}")
            
            # Call R script for analysis
            result = await self._call_r_script(analysis_type, task)
            
            # Update metrics
            self.status.metrics["analyses_completed"] = \
                self.status.metrics.get("analyses_completed", 0) + 1
            
            return result
            
        except Exception as e:
            self.status.last_error = str(e)
            logger.error(f"Statistical analysis failed: {e}")
            raise
    
    async def _call_r_script(self, script_name: str, args: Dict) -> Dict:
        """Call R script asynchronously"""
        return await asyncio.to_thread(
            subprocess.run,
            ["Rscript", f"scripts/tools/{script_name}.R", json.dumps(args)],
            capture_output=True,
            text=True
        )


class TestAutomationAgent(BackgroundAgent):
    """Agent for running automated tests"""
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """Run tests based on trigger"""
        trigger = task.get("trigger", "manual")
        test_suite = task.get("suite", "all")
        
        logger.info(f"Running {test_suite} tests triggered by {trigger}")
        
        # Run tests in subprocess
        cmd = [sys.executable, "tests/run_all_tests.py"]
        if test_suite != "all":
            cmd.append(test_suite)
            
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True
        )
        
        # Parse results
        success = result.returncode == 0
        self.status.metrics["tests_run"] = self.status.metrics.get("tests_run", 0) + 1
        self.status.metrics["tests_passed"] = \
            self.status.metrics.get("tests_passed", 0) + (1 if success else 0)
        
        return {
            "success": success,
            "output": result.stdout,
            "errors": result.stderr
        }


class PerformanceMonitorAgent(BackgroundAgent):
    """Agent for monitoring system performance"""
    
    async def start(self):
        """Start continuous monitoring"""
        await super().start()
        self.monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def _monitor_loop(self):
        """Continuous monitoring loop"""
        interval = self.config.resources.get("interval", 300)
        
        while not self.stop_event.is_set():
            try:
                metrics = await self._collect_metrics()
                await self._process_metrics(metrics)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect system metrics"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids()),
            "r_processes": len([p for p in psutil.process_iter(['name']) 
                               if 'Rscript' in p.info.get('name', '')])
        }
    
    async def _process_metrics(self, metrics: Dict[str, Any]):
        """Process and store metrics"""
        # Check thresholds
        if metrics["cpu_percent"] > 80:
            logger.warning(f"High CPU usage: {metrics['cpu_percent']}%")
        if metrics["memory_percent"] > 80:
            logger.warning(f"High memory usage: {metrics['memory_percent']}%")
            
        # Store metrics
        self.status.metrics = metrics
        
        # Save to file
        metrics_file = Path("metrics/performance.json")
        metrics_file.parent.mkdir(exist_ok=True)
        
        with open(metrics_file, "a") as f:
            f.write(json.dumps(metrics) + "\n")


class CochraneGuidanceAgent(BackgroundAgent):
    """Agent for Cochrane methodology guidance"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.knowledge_base = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> Dict:
        """Load Cochrane knowledge base"""
        # This would load the enhanced guidance from R
        return {
            "heterogeneity_thresholds": {
                "low": 25,
                "moderate": 50,
                "substantial": 75
            },
            "minimum_studies": {
                "meta_analysis": 2,
                "publication_bias": 10,
                "meta_regression": 10
            }
        }
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """Provide Cochrane-based recommendations"""
        analysis_context = task.get("context", {})
        
        recommendations = []
        
        # Check heterogeneity
        i_squared = analysis_context.get("i_squared", 0)
        if i_squared > 75:
            recommendations.append({
                "type": "heterogeneity",
                "severity": "high",
                "message": "Considerable heterogeneity detected (I² > 75%)",
                "action": "Consider not pooling studies or investigating sources"
            })
        
        # Check study count
        n_studies = analysis_context.get("n_studies", 0)
        if n_studies < 10 and task.get("test_publication_bias"):
            recommendations.append({
                "type": "publication_bias",
                "severity": "warning",
                "message": "Too few studies for reliable bias assessment",
                "action": "Interpret bias tests with caution"
            })
        
        return {"recommendations": recommendations}


class LLMOrchestrationAgent(BackgroundAgent):
    """Agent for orchestrating LLM interactions"""
    
    async def execute(self, task: Dict[str, Any]) -> Any:
        """Route and manage LLM requests"""
        provider = task.get("provider", os.getenv("DEFAULT_LLM_PROVIDER", "anthropic"))
        
        try:
            if provider == "anthropic":
                return await self._call_anthropic(task)
            elif provider == "openai":
                return await self._call_openai(task)
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
        except Exception as e:
            # Try fallback provider
            fallback = os.getenv("FALLBACK_LLM_PROVIDER")
            if fallback and fallback != provider:
                logger.warning(f"Primary LLM failed, trying fallback: {fallback}")
                task["provider"] = fallback
                return await self.execute(task)
            raise
    
    async def _call_anthropic(self, task: Dict) -> Dict:
        """Call Anthropic API"""
        # Implementation would use anthropic SDK
        return {"response": "Anthropic response", "provider": "anthropic"}
    
    async def _call_openai(self, task: Dict) -> Dict:
        """Call OpenAI API"""
        # Implementation would use openai SDK
        return {"response": "OpenAI response", "provider": "openai"}


class AgentManager:
    """Manages all background agents"""
    
    def __init__(self, config_path: str = "config/agent-environment.yaml"):
        self.config = self._load_config(config_path)
        self.agents: Dict[str, BackgroundAgent] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.loop = asyncio.new_event_loop()
        self.running = False
        
    def _load_config(self, config_path: str) -> Dict:
        """Load agent configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _create_agent(self, name: str, config: Dict) -> BackgroundAgent:
        """Create agent instance based on configuration"""
        agent_config = AgentConfig(
            name=name,
            type=config.get("type", "background"),
            enabled=config.get("enabled", True),
            capabilities=config.get("capabilities", []),
            triggers=config.get("triggers", []),
            resources=config.get("resources", {}),
            schedule=config.get("schedule")
        )
        
        # Map agent types to classes
        agent_classes = {
            "statistical_agent": StatisticalAnalysisAgent,
            "test_automation_agent": TestAutomationAgent,
            "performance_agent": PerformanceMonitorAgent,
            "cochrane_agent": CochraneGuidanceAgent,
            "llm_orchestrator": LLMOrchestrationAgent
        }
        
        agent_class = agent_classes.get(name, BackgroundAgent)
        return agent_class(agent_config)
    
    async def start(self):
        """Start all enabled agents"""
        logger.info("Starting Agent Manager")
        self.running = True
        
        # Create and start agents
        for name, config in self.config.get("agents", {}).items():
            if config.get("enabled", True):
                agent = self._create_agent(name, config)
                self.agents[name] = agent
                await agent.start()
                logger.info(f"Started agent: {name}")
        
        # Start monitoring loop
        asyncio.create_task(self._monitor_agents())
    
    async def stop(self):
        """Stop all agents"""
        logger.info("Stopping Agent Manager")
        self.running = False
        
        # Stop all agents
        for name, agent in self.agents.items():
            await agent.stop()
            logger.info(f"Stopped agent: {name}")
        
        self.executor.shutdown(wait=True)
    
    async def _monitor_agents(self):
        """Monitor agent health and restart if needed"""
        while self.running:
            for name, agent in self.agents.items():
                status = agent.get_status()
                
                # Restart failed agents
                if status.status == "failed":
                    logger.warning(f"Restarting failed agent: {name}")
                    await agent.stop()
                    await agent.start()
                
                # Check resource limits
                if hasattr(agent, "process") and agent.process:
                    try:
                        proc = psutil.Process(agent.process.pid)
                        if proc.memory_percent() > 50:  # 50% of system memory
                            logger.warning(f"Agent {name} using too much memory")
                            await self.restart_agent(name)
                    except psutil.NoSuchProcess:
                        pass
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def restart_agent(self, name: str):
        """Restart a specific agent"""
        if name in self.agents:
            agent = self.agents[name]
            await agent.stop()
            await agent.start()
            logger.info(f"Restarted agent: {name}")
    
    async def execute_task(self, agent_name: str, task: Dict[str, Any]) -> Any:
        """Execute a task on a specific agent"""
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        agent = self.agents[agent_name]
        return await agent.execute(task)
    
    def get_status(self) -> Dict[str, AgentStatus]:
        """Get status of all agents"""
        return {name: agent.get_status() for name, agent in self.agents.items()}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics from all agents"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "agents": {}
        }
        
        for name, agent in self.agents.items():
            status = agent.get_status()
            metrics["agents"][name] = {
                "status": status.status,
                "metrics": status.metrics,
                "last_error": status.last_error
            }
        
        return metrics


async def main():
    """Main entry point for agent manager"""
    manager = AgentManager()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(manager.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start manager
        await manager.start()
        
        # Keep running
        while manager.running:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Agent manager error: {e}")
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
