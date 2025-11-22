"""Web interface for ProcOrg."""

import threading
import time
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from .storage import Storage
from .manager import ProcessManager
from .scheduler import Scheduler


app = Flask(__name__)
app.config['SECRET_KEY'] = 'procorg-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

storage = Storage()
manager = ProcessManager(storage)
scheduler = Scheduler(storage, manager)


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/processes')
def get_processes():
    """Get all processes with their status."""
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
def get_process(name):
    """Get detailed information about a process."""
    proc = storage.get_process(name)
    if not proc:
        return jsonify({'error': 'Process not found'}), 404

    status = manager.get_process_status(name)

    return jsonify({
        **proc,
        'status': status
    })


@app.route('/api/processes', methods=['POST'])
def register_process():
    """Register a new process."""
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
    import os
    if not os.path.exists(script_path):
        return jsonify({'success': False, 'error': 'Script file not found'}), 404

    try:
        storage.register_process(name, script_path, cron_expr, description)
        return jsonify({'success': True, 'name': name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/processes/<name>', methods=['DELETE'])
def unregister_process(name):
    """Unregister a process."""
    success = storage.unregister_process(name)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Process not found'}), 404


@app.route('/api/processes/<name>/run', methods=['POST'])
def run_process(name):
    """Run a process manually."""
    execution = manager.run_process(name)

    if execution:
        return jsonify({
            'success': True,
            'execution': execution.get_info()
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to start process'}), 500


@app.route('/api/processes/<name>/stop', methods=['POST'])
def stop_process(name):
    """Stop a running process."""
    success = manager.stop_process(name)

    return jsonify({'success': success})


@app.route('/api/processes/<name>/logs/<stream>')
def get_logs(name, stream):
    """Get logs for a process."""
    lines = request.args.get('lines', 100, type=int)
    log_content = manager.get_latest_logs(name, stream, lines)

    return jsonify({
        'name': name,
        'stream': stream,
        'content': log_content
    })


@app.route('/api/scheduler')
def get_scheduler_info():
    """Get scheduler information."""
    return jsonify(scheduler.get_schedule_info())


@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """Start the scheduler."""
    scheduler.start()
    return jsonify({'success': True})


@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Stop the scheduler."""
    scheduler.stop()
    return jsonify({'success': True})


def broadcast_status_updates():
    """Background thread to broadcast status updates to connected clients."""
    while True:
        try:
            statuses = manager.get_all_statuses()
            socketio.emit('status_update', statuses)
            time.sleep(2)
        except Exception as e:
            print(f"Error broadcasting status: {e}")
            time.sleep(5)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected')
    emit('connected', {'data': 'Connected to ProcOrg'})


@socketio.on('subscribe_logs')
def handle_subscribe_logs(data):
    """Subscribe to real-time log updates for a process."""
    name = data.get('name')
    stream = data.get('stream', 'stdout')

    print(f"Client subscribed to logs for {name}/{stream}")

    # Send initial logs
    log_content = manager.get_latest_logs(name, stream, 100)
    emit('log_update', {
        'name': name,
        'stream': stream,
        'content': log_content
    })


def run_server(host='0.0.0.0', port=5000, debug=False):
    """Run the web server."""
    # Start background thread for status updates
    status_thread = threading.Thread(target=broadcast_status_updates, daemon=True)
    status_thread.start()

    print(f"Starting ProcOrg web server on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_server(debug=True)
