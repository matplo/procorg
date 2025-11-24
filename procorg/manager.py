"""Core process management functionality."""

import subprocess
import threading
import psutil
import os
import pwd
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
from .storage import Storage


def demote(uid: int, gid: int):
    """Demote process privileges to specified uid/gid.

    This function is used as preexec_fn in subprocess.Popen to ensure
    the child process runs with the correct user privileges.

    Args:
        uid: User ID to run as
        gid: Group ID to run as
    """
    def set_ids():
        os.setgid(gid)
        os.setuid(uid)
    return set_ids


class ProcessExecution:
    """Represents a single execution of a process."""

    def __init__(self, name: str, script_path: str, storage: Storage, uid: Optional[int] = None, args: Optional[List[str]] = None):
        self.name = name
        self.script_path = script_path
        self.storage = storage
        self.uid = uid if uid is not None else os.getuid()
        self.args = args or []
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.exit_code: Optional[int] = None
        self.status = "pending"

    def start(self) -> bool:
        """Start the process execution."""
        try:
            stdout_log = self.storage.get_execution_log_path(self.name, self.execution_id, "stdout")
            stderr_log = self.storage.get_execution_log_path(self.name, self.execution_id, "stderr")

            stdout_file = open(stdout_log, 'w')
            stderr_file = open(stderr_log, 'w')

            # Prepare preexec_fn for privilege demotion if running as root
            preexec_fn = None
            if os.getuid() == 0:  # Running as root
                # Get the GID for the target user
                try:
                    user_info = pwd.getpwuid(self.uid)
                    gid = user_info.pw_gid
                    preexec_fn = demote(self.uid, gid)
                    print(f"Running process {self.name} as uid={self.uid}, gid={gid}")
                except KeyError:
                    print(f"Warning: Could not find user info for uid {self.uid}, running as current user")

            # Build command with optional arguments
            cmd = ['/bin/bash', self.script_path] + self.args

            self.process = subprocess.Popen(
                cmd,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=os.path.dirname(self.script_path) or '.',
                preexec_fn=preexec_fn
            )

            self.pid = self.process.pid
            self.start_time = datetime.now()
            self.status = "running"

            # Save PID to file for cross-request status tracking
            pid_file = self.storage.logs_dir / self.name / f"{self.execution_id}.pid"
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            with open(pid_file, 'w') as f:
                f.write(str(self.pid))

            # Save args to file for cross-request status tracking
            if self.args:
                args_file = self.storage.logs_dir / self.name / f"{self.execution_id}.args"
                with open(args_file, 'w') as f:
                    f.write('\n'.join(self.args))

            # Start a thread to monitor completion
            # Note: Using daemon=False so the thread can complete even if the request handler returns
            t = threading.Thread(target=self._monitor, args=(stdout_file, stderr_file), daemon=False)
            t.start()

            return True
        except Exception as e:
            self.status = "failed"
            self.exit_code = -1
            print(f"Failed to start process {self.name}: {e}")
            return False

    def _monitor(self, stdout_file, stderr_file):
        """Monitor process completion."""
        import time

        try:
            # Use poll() in a loop instead of wait() to avoid hanging on unclosed pipes
            # This is necessary because child processes may spawn grandchildren that keep
            # stdout/stderr file descriptors open, causing wait() to hang indefinitely
            while True:
                self.exit_code = self.process.poll()
                if self.exit_code is not None:
                    break
                time.sleep(0.1)  # Check every 100ms

            self.end_time = datetime.now()
            self.status = "completed" if self.exit_code == 0 else "failed"
        except Exception as e:
            self.status = "failed"
            self.exit_code = -1
            print(f"Error monitoring process {self.name}: {e}")
        finally:
            stdout_file.close()
            stderr_file.close()

            # Save exit code to file for persistence
            exitcode_file = self.storage.logs_dir / self.name / f"{self.execution_id}.exitcode"
            try:
                with open(exitcode_file, 'w') as f:
                    f.write(str(self.exit_code if self.exit_code is not None else -1))
            except Exception as e:
                print(f"Failed to save exit code: {e}")

            # Remove PID file when process completes
            pid_file = self.storage.logs_dir / self.name / f"{self.execution_id}.pid"
            if pid_file.exists():
                pid_file.unlink()

    def stop(self) -> bool:
        """Stop the running process."""
        if self.process and self.status == "running":
            try:
                parent = psutil.Process(self.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()

                # Wait a bit, then kill if still alive
                parent.wait(timeout=5)
                self.status = "stopped"
                self.end_time = datetime.now()
                return True
            except psutil.NoSuchProcess:
                self.status = "stopped"
                return True
            except Exception as e:
                print(f"Error stopping process {self.name}: {e}")
                return False
        return False

    def get_info(self) -> Dict:
        """Get execution information."""
        return {
            "execution_id": self.execution_id,
            "name": self.name,
            "pid": self.pid,
            "status": self.status,
            "args": self.args,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "exit_code": self.exit_code,
            "duration": (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else None
        }


class ProcessManager:
    """Manages process executions."""

    def __init__(self, storage: Storage, uid: Optional[int] = None):
        self.storage = storage
        self.uid = uid if uid is not None else os.getuid()
        self.executions: Dict[str, List[ProcessExecution]] = {}
        self.lock = threading.Lock()

    def run_process(self, name: str, args: Optional[List[str]] = None) -> Optional[ProcessExecution]:
        """Execute a registered process."""
        process_def = self.storage.get_process(name)

        if not process_def:
            print(f"Process {name} not found in registry")
            return None

        if not process_def.get("enabled", True):
            print(f"Process {name} is disabled")
            return None

        script_path = process_def["script_path"]

        if not os.path.exists(script_path):
            print(f"Script not found: {script_path}")
            return None

        execution = ProcessExecution(name, script_path, self.storage, uid=self.uid, args=args)

        with self.lock:
            if name not in self.executions:
                self.executions[name] = []
            self.executions[name].append(execution)

        if execution.start():
            return execution
        return None

    def get_running_execution(self, name: str) -> Optional[ProcessExecution]:
        """Get the currently running execution for a process."""
        with self.lock:
            if name in self.executions:
                for execution in reversed(self.executions[name]):
                    if execution.status == "running":
                        return execution
        return None

    def stop_process(self, name: str) -> bool:
        """Stop a running process."""
        # First try in-memory executions
        execution = self.get_running_execution(name)
        if execution:
            return execution.stop()

        # If not in memory, check filesystem for PID file
        execution_id = self._get_latest_execution_id(name)

        if execution_id:
            pid_file = self.storage.logs_dir / name / f"{execution_id}.pid"

            if pid_file.exists():
                try:
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())

                    # Use psutil to stop the process and its children
                    try:
                        parent = psutil.Process(pid)

                        children = parent.children(recursive=True)

                        for child in children:
                            child.terminate()
                        parent.terminate()

                        # Wait a bit, then kill if still alive
                        parent.wait(timeout=5)

                        # Clean up PID file (may fail if owned by different user)
                        try:
                            pid_file.unlink()
                        except PermissionError:
                            pass  # Process was stopped, PID file cleanup is not critical

                        # Write exit code indicating manual stop
                        try:
                            exitcode_file = self.storage.logs_dir / name / f"{execution_id}.exitcode"
                            with open(exitcode_file, 'w') as f:
                                f.write("-15")  # SIGTERM
                        except PermissionError:
                            pass  # Exit code writing is not critical

                        return True
                    except psutil.NoSuchProcess:
                        # Process already stopped, clean up PID file
                        try:
                            pid_file.unlink()
                        except PermissionError:
                            pass
                        return True
                    except psutil.TimeoutExpired:
                        # Force kill if didn't stop gracefully
                        for child in parent.children(recursive=True):
                            child.kill()
                        parent.kill()
                        try:
                            pid_file.unlink()
                        except PermissionError:
                            pass
                        return True
                except (ValueError, FileNotFoundError) as e:
                    print(f"Error reading PID file: {e}")
                    return False
                except Exception as e:
                    print(f"Error stopping process {name}: {e}")
                    return False

        return False

    def get_process_status(self, name: str) -> Dict:
        """Get the status of a process."""
        with self.lock:
            executions = self.executions.get(name, [])

            # Check in-memory executions first
            latest_in_memory = executions[-1] if executions else None
            is_running_in_memory = any(e.status == "running" for e in executions)

            # If no in-memory executions, check filesystem for latest
            latest_execution_info = None
            is_running = is_running_in_memory

            if latest_in_memory:
                latest_execution_info = latest_in_memory.get_info()
            else:
                # Scan filesystem for latest execution
                execution_id = self._get_latest_execution_id(name)
                if execution_id:
                    # Check if this execution is still running by checking PID
                    pid_file = self.storage.logs_dir / name / f"{execution_id}.pid"
                    if pid_file.exists():
                        try:
                            with open(pid_file, 'r') as f:
                                pid = int(f.read().strip())
                            # Check if process is still running
                            try:
                                os.kill(pid, 0)  # Doesn't kill, just checks if exists
                                is_running = True
                                status = "running"
                            except OSError:
                                is_running = False
                                status = "completed"  # Or could check exit code
                        except (ValueError, FileNotFoundError):
                            is_running = False
                            status = "completed"
                    else:
                        is_running = False
                        status = "completed"

                    # Parse start time from execution_id (format: YYYYMMDD_HHMMSS_microseconds)
                    try:
                        # execution_id format: 20231121_143025_123456
                        date_part = execution_id.split('_')[0]  # YYYYMMDD
                        time_part = execution_id.split('_')[1]  # HHMMSS
                        start_time_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").isoformat()
                    except (IndexError, ValueError):
                        start_time = None

                    # Read exit code from file if available
                    exit_code = None
                    exitcode_file = self.storage.logs_dir / name / f"{execution_id}.exitcode"
                    if exitcode_file.exists():
                        try:
                            with open(exitcode_file, 'r') as f:
                                exit_code = int(f.read().strip())
                        except (ValueError, FileNotFoundError):
                            pass

                    # Build execution info from filesystem
                    latest_execution_info = {
                        "execution_id": execution_id,
                        "name": name,
                        "pid": None,
                        "status": status if is_running else "completed",
                        "start_time": start_time,
                        "end_time": None,
                        "exit_code": exit_code,
                        "duration": None
                    }

            return {
                "name": name,
                "latest_execution": latest_execution_info,
                "total_executions": len(executions),
                "running": is_running
            }

    def get_all_statuses(self) -> List[Dict]:
        """Get status of all processes."""
        processes = self.storage.list_processes()
        return [self.get_process_status(p["name"]) for p in processes]

    def get_execution_logs(self, name: str, execution_id: str, stream: str = "stdout") -> str:
        """Read logs for a specific execution."""
        log_path = self.storage.get_execution_log_path(name, execution_id, stream)

        if log_path.exists():
            with open(log_path, 'r') as f:
                return f.read()
        return ""

    def get_latest_logs(self, name: str, stream: str = "stdout", lines: int = 100) -> str:
        """Get the latest logs for a process."""
        # First check in-memory executions
        with self.lock:
            executions = self.executions.get(name, [])
            if executions:
                latest = executions[-1]
                log_path = self.storage.get_execution_log_path(name, latest.execution_id, stream)

                if log_path.exists():
                    with open(log_path, 'r') as f:
                        all_lines = f.readlines()
                        return ''.join(all_lines[-lines:])

        # If not in memory, scan filesystem for latest execution
        execution_id = self._get_latest_execution_id(name)
        if execution_id:
            log_path = self.storage.get_execution_log_path(name, execution_id, stream)
            if log_path.exists():
                with open(log_path, 'r') as f:
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:])

        return ""

    def _get_latest_execution_id(self, name: str) -> Optional[str]:
        """Find the latest execution ID by scanning the logs directory."""
        exec_dir = self.storage.logs_dir / name
        if not exec_dir.exists():
            return None

        # Find all stdout log files
        log_files = list(exec_dir.glob("*.stdout.log"))
        if not log_files:
            return None

        # Extract execution IDs and sort
        execution_ids = [f.stem.replace('.stdout', '') for f in log_files]
        execution_ids.sort(reverse=True)

        return execution_ids[0] if execution_ids else None
