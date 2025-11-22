"""Cron-based process scheduling."""

import threading
import time
from datetime import datetime
from croniter import croniter
from typing import Dict, Optional
from .storage import Storage
from .manager import ProcessManager


class Scheduler:
    """Manages scheduled process executions based on cron expressions."""

    def __init__(self, storage: Storage, manager: ProcessManager):
        self.storage = storage
        self.manager = manager
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.next_runs: Dict[str, datetime] = {}
        self.lock = threading.Lock()

    def start(self):
        """Start the scheduler."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Scheduler stopped")

    def _run(self):
        """Main scheduler loop."""
        while self.running:
            try:
                self._check_and_run()
                time.sleep(1)  # Check every second
            except Exception as e:
                print(f"Scheduler error: {e}")

    def _check_and_run(self):
        """Check if any processes should run and execute them."""
        processes = self.storage.list_processes()

        for process in processes:
            name = process["name"]
            cron_expr = process.get("cron_expr")

            if not cron_expr or not process.get("enabled", True):
                continue

            # Check if this process is already running
            if self.manager.get_running_execution(name):
                continue

            try:
                now = datetime.now()

                # Initialize next run time if not set
                if name not in self.next_runs:
                    cron = croniter(cron_expr, now)
                    self.next_runs[name] = cron.get_next(datetime)

                # Check if it's time to run
                if now >= self.next_runs[name]:
                    print(f"Scheduled execution of {name} at {now}")
                    self.manager.run_process(name)

                    # Calculate next run time
                    cron = croniter(cron_expr, now)
                    self.next_runs[name] = cron.get_next(datetime)

            except Exception as e:
                print(f"Error scheduling {name}: {e}")

    def get_next_run(self, name: str) -> Optional[datetime]:
        """Get the next scheduled run time for a process."""
        with self.lock:
            return self.next_runs.get(name)

    def get_schedule_info(self) -> Dict:
        """Get information about scheduled processes."""
        processes = self.storage.list_processes()
        scheduled = []

        for process in processes:
            name = process["name"]
            cron_expr = process.get("cron_expr")

            if cron_expr and process.get("enabled", True):
                next_run = self.next_runs.get(name)
                scheduled.append({
                    "name": name,
                    "cron_expr": cron_expr,
                    "next_run": next_run.isoformat() if next_run else None
                })

        return {
            "running": self.running,
            "scheduled_processes": scheduled
        }
