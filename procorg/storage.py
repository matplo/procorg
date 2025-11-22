"""Storage layer for process registry and state."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class Storage:
    """File-based storage for process definitions and state."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir = self.data_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.data_dir / "processes.json"

        if not self.registry_file.exists():
            self._save_registry({})

    def _save_registry(self, registry: Dict) -> None:
        """Save the process registry to disk."""
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)

    def _load_registry(self) -> Dict:
        """Load the process registry from disk."""
        with open(self.registry_file, 'r') as f:
            return json.load(f)

    def register_process(self, name: str, script_path: str, cron_expr: Optional[str] = None,
                        description: str = "") -> None:
        """Register a new process."""
        registry = self._load_registry()

        registry[name] = {
            "name": name,
            "script_path": script_path,
            "cron_expr": cron_expr,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "enabled": True
        }

        self._save_registry(registry)

    def unregister_process(self, name: str) -> bool:
        """Remove a process from the registry."""
        registry = self._load_registry()

        if name in registry:
            del registry[name]
            self._save_registry(registry)
            return True
        return False

    def get_process(self, name: str) -> Optional[Dict]:
        """Get a specific process definition."""
        registry = self._load_registry()
        return registry.get(name)

    def list_processes(self) -> List[Dict]:
        """List all registered processes."""
        registry = self._load_registry()
        return list(registry.values())

    def update_process(self, name: str, **kwargs) -> bool:
        """Update process attributes."""
        registry = self._load_registry()

        if name not in registry:
            return False

        for key, value in kwargs.items():
            if key in registry[name]:
                registry[name][key] = value

        self._save_registry(registry)
        return True

    def get_log_path(self, name: str, stream: str = "stdout") -> Path:
        """Get the log file path for a process."""
        return self.logs_dir / f"{name}.{stream}.log"

    def get_execution_log_path(self, name: str, execution_id: str, stream: str = "stdout") -> Path:
        """Get the log file path for a specific execution."""
        exec_dir = self.logs_dir / name
        exec_dir.mkdir(parents=True, exist_ok=True)
        return exec_dir / f"{execution_id}.{stream}.log"
