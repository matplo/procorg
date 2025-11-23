"""Web interface for ProcOrg."""

import threading
import time
import os
import secrets
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_session import Session
from .storage import Storage
from .manager import ProcessManager
from .scheduler import Scheduler
from .auth import (
    authenticate_user, get_current_user, require_auth,
    init_session, clear_session
)


app = Flask(__name__)

# Generate secure random secret key if not set
app.config['SECRET_KEY'] = os.environ.get('PROCORG_SECRET_KEY') or secrets.token_hex(32)

# Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './data/flask_session'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

Session(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Note: No global storage/manager - created per-user in routes


@app.route('/')
def index():
    """Serve the main page (requires authentication)."""
    user = get_current_user()
    if user is None:
        return redirect(url_for('login_page'))
    return render_template('index.html')


@app.route('/login')
def login_page():
    """Serve the login page."""
    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user and create session."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400

    user = authenticate_user(username, password)
    if user:
        init_session(user)
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Invalid username or password'
        }), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    """Clear session and log out."""
    clear_session()
    return jsonify({'success': True})


@app.route('/api/whoami')
def whoami():
    """Get current user information."""
    user = get_current_user()
    if user:
        return jsonify({
            'authenticated': True,
            'user': user.to_dict()
        })
    else:
        return jsonify({'authenticated': False}), 401


@app.route('/api/processes')
@require_auth
def get_processes():
    """Get all processes with their status (user-specific or all for root)."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)

    # Root can see all processes
    if user.is_root:
        processes = storage.list_all_processes()
    else:
        processes = storage.list_processes()

    statuses = manager.get_all_statuses()

    # Merge process definitions with status
    result = []
    for proc in processes:
        name = proc['name']
        status = next((s for s in statuses if s['name'] == name), None)

        result.append({
            **proc,
            'status': status
        })

    return jsonify(result)


@app.route('/api/processes/<name>')
@require_auth
def get_process(name):
    """Get detailed information about a process."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)

    proc = storage.get_process(name)
    if not proc:
        return jsonify({'error': 'Process not found'}), 404

    # Verify ownership (non-root can only see their own)
    # Check ownership: processes without owner_uid are treated as belonging to current user (backward compatibility)
    proc_owner = proc.get('owner_uid')
    if not user.is_root and proc_owner is not None and proc_owner != user.uid:
        return jsonify({'error': 'Permission denied'}), 403

    status = manager.get_process_status(name)

    return jsonify({
        **proc,
        'status': status
    })


@app.route('/api/processes', methods=['POST'])
@require_auth
def register_process():
    """Register a new process."""
    user = get_current_user()
    storage = Storage(uid=user.uid)

    data = request.get_json()

    name = data.get('name')
    script_path = data.get('script_path')
    cron_expr = data.get('cron_expr')
    description = data.get('description', '')

    if not name or not script_path:
        return jsonify({'success': False, 'error': 'Name and script_path are required'}), 400

    # Check if process already exists
    if storage.get_process(name):
        return jsonify({'success': False, 'error': 'Process already exists'}), 409

    # Validate script path exists
    if not os.path.exists(script_path):
        return jsonify({'success': False, 'error': 'Script file not found'}), 404

    try:
        storage.register_process(name, script_path, cron_expr, description)
        return jsonify({'success': True, 'name': name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/processes/<name>', methods=['DELETE'])
@require_auth
def unregister_process(name):
    """Unregister a process."""
    user = get_current_user()
    storage = Storage(uid=user.uid)

    # Verify ownership before deleting
    proc = storage.get_process(name)
    if not proc:
        return jsonify({'success': False, 'error': 'Process not found'}), 404

    # Check ownership: processes without owner_uid are treated as belonging to current user (backward compatibility)
    proc_owner = proc.get('owner_uid')
    if not user.is_root and proc_owner is not None and proc_owner != user.uid:
        return jsonify({'error': 'Permission denied'}), 403

    success = storage.unregister_process(name)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Process not found'}), 404


@app.route('/api/processes/<name>/run', methods=['POST'])
@require_auth
def run_process(name):
    """Run a process manually."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)

    # Get optional args from request
    data = request.get_json() or {}
    args = data.get('args', [])

    # Verify ownership
    proc = storage.get_process(name)
    if not proc:
        return jsonify({'success': False, 'error': 'Process not found'}), 404

    # Check ownership: processes without owner_uid are treated as belonging to current user (backward compatibility)
    proc_owner = proc.get('owner_uid')
    if not user.is_root and proc_owner is not None and proc_owner != user.uid:
        return jsonify({'error': 'Permission denied'}), 403

    execution = manager.run_process(name, args=args)

    if execution:
        return jsonify({
            'success': True,
            'execution': execution.get_info()
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to start process'}), 500


@app.route('/api/processes/running')
@require_auth
def get_running_processes():
    """Get all running processes grouped by name."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)

    # Get all processes
    if user.is_root:
        processes = storage.list_all_processes()
    else:
        processes = storage.list_processes()

    # Build grouped running processes
    running_groups = []
    for proc in processes:
        name = proc['name']

        # Get all running executions for this process from in-memory
        running_execs = []
        with manager.lock:
            if name in manager.executions:
                for execution in manager.executions[name]:
                    if execution.status == "running":
                        running_execs.append(execution.get_info())

        # Also check filesystem for ALL running executions started by other requests
        exec_dir = storage.logs_dir / name
        if exec_dir.exists():
            # Find all PID files for this process
            pid_files = list(exec_dir.glob("*.pid"))
            for pid_file in pid_files:
                # Extract execution_id from filename (e.g., "20231121_143025_123456.pid")
                execution_id = pid_file.stem

                # Check if already in running_execs from in-memory
                if any(e['execution_id'] == execution_id for e in running_execs):
                    continue

                try:
                    with open(pid_file, 'r') as f:
                        pid = int(f.read().strip())

                    # Check if process is still running
                    try:
                        os.kill(pid, 0)
                        # Process exists, parse execution info from filesystem
                        date_part = execution_id.split('_')[0]
                        time_part = execution_id.split('_')[1]
                        start_time_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                        from datetime import datetime
                        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").isoformat()

                        running_execs.append({
                            "execution_id": execution_id,
                            "name": name,
                            "pid": pid,
                            "status": "running",
                            "args": [],
                            "start_time": start_time,
                            "end_time": None,
                            "exit_code": None,
                            "duration": None
                        })
                    except OSError:
                        pass  # Process not running
                except (ValueError, FileNotFoundError):
                    pass

        if running_execs:
            running_groups.append({
                'name': name,
                'description': proc.get('description', ''),
                'script_path': proc['script_path'],
                'instances': running_execs
            })

    return jsonify(running_groups)


@app.route('/api/processes/<name>/stop', methods=['POST'])
@require_auth
def stop_process(name):
    """Stop a running process."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)

    # Verify ownership
    proc = storage.get_process(name)
    if not proc:
        return jsonify({'success': False, 'error': 'Process not found'}), 404

    # Check ownership: processes without owner_uid are treated as belonging to current user (backward compatibility)
    proc_owner = proc.get('owner_uid')
    if not user.is_root and proc_owner is not None and proc_owner != user.uid:
        return jsonify({'error': 'Permission denied'}), 403

    success = manager.stop_process(name)

    return jsonify({'success': success})


@app.route('/api/processes/<name>/logs/<stream>')
@require_auth
def get_logs(name, stream):
    """Get logs for a process."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)

    # Verify ownership
    proc = storage.get_process(name)
    if not proc:
        return jsonify({'error': 'Process not found'}), 404

    # Check ownership: processes without owner_uid are treated as belonging to current user (backward compatibility)
    proc_owner = proc.get('owner_uid')
    if not user.is_root and proc_owner is not None and proc_owner != user.uid:
        return jsonify({'error': 'Permission denied'}), 403

    lines = request.args.get('lines', 100, type=int)
    log_content = manager.get_latest_logs(name, stream, lines)

    return jsonify({
        'name': name,
        'stream': stream,
        'content': log_content
    })


@app.route('/api/scheduler')
@require_auth
def get_scheduler_info():
    """Get scheduler information."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)
    scheduler = Scheduler(storage, manager)

    return jsonify(scheduler.get_schedule_info())


@app.route('/api/scheduler/start', methods=['POST'])
@require_auth
def start_scheduler():
    """Start the scheduler."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)
    scheduler = Scheduler(storage, manager)

    scheduler.start()
    return jsonify({'success': True})


@app.route('/api/scheduler/stop', methods=['POST'])
@require_auth
def stop_scheduler():
    """Stop the scheduler."""
    user = get_current_user()
    storage = Storage(uid=user.uid)
    manager = ProcessManager(storage, uid=user.uid)
    scheduler = Scheduler(storage, manager)

    scheduler.stop()
    return jsonify({'success': True})


def broadcast_status_updates():
    """Background thread to broadcast status updates to connected clients.

    Note: Disabled in multi-user mode. Status updates are handled via
    client-side polling of /api/processes endpoint instead.
    """
    # Disabled - no global manager in multi-user mode
    pass


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected')
    emit('connected', {'data': 'Connected to ProcOrg'})


@socketio.on('subscribe_logs')
def handle_subscribe_logs(data):
    """Subscribe to real-time log updates for a process.

    Note: In multi-user mode, clients should use the /api/processes/<name>/logs/<stream>
    endpoint instead. This WebSocket handler is disabled.
    """
    name = data.get('name')
    stream = data.get('stream', 'stdout')

    print(f"Client subscribed to logs for {name}/{stream} (WebSocket log streaming disabled in multi-user mode)")

    # Disabled - clients should use REST API instead
    emit('log_update', {
        'name': name,
        'stream': stream,
        'content': 'WebSocket log streaming disabled. Please use the REST API endpoint.'
    })


def run_server(host='0.0.0.0', port=9777, debug=False):
    """Run the web server."""
    # Note: Background status updates disabled in multi-user mode
    # Status updates are handled via client-side polling

    print(f"Starting ProcOrg web server on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_server(debug=True)
