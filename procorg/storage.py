"""Storage layer for process registry and state."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pwd


class Storage:
    """File-based storage for process definitions and state."""

    def __init__(self, data_dir: str = "data", uid: Optional[int] = None):
        """Initialize storage for a specific user.

        Args:
            data_dir: Base data directory
            uid: User ID for multi-user support. If None, uses current user.
        """
        # Get current user if uid not specified
        if uid is None:
            uid = os.getuid()

        self.uid = uid
        self.base_data_dir = Path(data_dir)

        # Multi-user structure: data/users/<uid>/
        self.data_dir = self.base_data_dir / "users" / str(uid)
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
            "enabled": True,
            "owner_uid": self.uid  # Track process owner
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

    def list_all_users(self) -> List[int]:
        """List all user IDs that have registered processes (root only).

        Returns:
            List of UIDs

        Raises:
            PermissionError: If called by non-root user
        """
        if self.uid != 0:
            raise PermissionError("Only root can list all users")

        users_dir = self.base_data_dir / "users"
        if not users_dir.exists():
            return []

        uids = []
        for uid_dir in users_dir.iterdir():
            if uid_dir.is_dir() and uid_dir.name.isdigit():
                uids.append(int(uid_dir.name))

        return sorted(uids)

    def list_all_processes(self) -> List[Dict]:
        """List processes from all users (root only).

        Each process dict includes 'owner_uid' field.

        Returns:
            List of all process definitions from all users

        Raises:
            PermissionError: If called by non-root user
        """
        if self.uid != 0:
            raise PermissionError("Only root can list all processes")

        all_processes = []
        for uid in self.list_all_users():
            user_storage = Storage(uid=uid)
            processes = user_storage.list_processes()

            # Add username for display
            for proc in processes:
                try:
                    username = pwd.getpwuid(uid).pw_name
                    proc['owner_username'] = username
                except KeyError:
                    proc['owner_username'] = f"uid:{uid}"

            all_processes.extend(processes)

        return all_processes

    def get_username(self) -> str:
        """Get the username for this storage instance's UID."""
        try:
            return pwd.getpwuid(self.uid).pw_name
        except KeyError:
            return f"uid:{self.uid}"
