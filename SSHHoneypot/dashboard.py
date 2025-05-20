from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import time
import threading
import os
import re
from collections import defaultdict
from honeypot import blacklist_manager
import logging

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
logging.getLogger('werkzeug').disabled = True
logging.getLogger('engineio').disabled = True
logging.getLogger('socketio').disabled = True

# tracks last file size
last_size = 0

@app.route("/")
def index():
    """Serve the attack monitoring page."""
    return render_template("index.html")

@app.route('/get-logs')
def get_logs():
    """Return the last N log entries."""
    try:
        with open('honeypot.log', 'r') as f:
            lines = f.readlines()
            return jsonify({'logs': lines[-100:] if len(lines) > 100 else lines})
    except FileNotFoundError:
        return jsonify({'logs': ["No log file found"]})

@app.route('/get-stats')
def get_stats():
    """Return attack statistics with proper categorization."""
    try:
        with open('honeypot.log', 'r') as f:
            logs = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return jsonify({'error': 'Log file not found'})

    attack_types = defaultdict(int)
    ip_addresses = defaultdict(int)
    total_attacks = 0

    for log in logs:
        is_attack = False
        ip_match = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', log)
        ip = ip_match.group() if ip_match else "Unknown"

        # check for knows attack patterns
        log_lower = log.lower()

        # sql injection
        if any(keyword in log_lower for keyword in ["sql injection", "sql injection attempt"]):
            attack_types["SQL Injection"] += 1
            is_attack = True

        # brute force
        elif any(keyword in log_lower for keyword in ["brute force", "failed login", "auth failed"]):
            attack_types["Brute Force"] += 1
            is_attack = True

        # reverse shell
        elif any(keyword in log_lower for keyword in ["reverse shell", "bash -i", "nc -e", "netcat", "/bin/sh", "/bin/bash"]):
            attack_types["Reverse Shell"] += 1
            is_attack = True

        # if is attack increase ips count
        if is_attack:
            ip_addresses[ip] += 1
            total_attacks += 1
        else:
            # other logs go to other
            attack_types["Non-Attack Traffic"] += 1

    return jsonify({
        'top_ips': dict(sorted(ip_addresses.items(), key=lambda x: x[1], reverse=True)[:5]),
        'attack_types': dict(sorted(
            {k: v for k, v in attack_types.items() if k != "Non-Attack Traffic"}.items(),
            key=lambda x: x[1],
            reverse=True
        )),
        'total_attacks': total_attacks, #amount of attacks
        'total_connections': len(logs)  #amount of logs
    })

@app.route('/blacklist', methods=['GET', 'POST'])
def manage_blacklist():
    if request.method == 'POST':
        data = request.get_json()
        if data['action'] == 'add':
            blacklist_manager.add(data['ip'])
        elif data['action'] == 'remove':
            blacklist_manager.remove(data['ip'])
        return jsonify({'status': 'success'})
    return jsonify({'blacklist': list(blacklist_manager.blacklisted_ips)})

def monitor_logs():
    """Monitor the log file for changes and emit new entries."""
    global last_size

    log_file = "honeypot.log"

    # creates the log file if doesnt exist
    if not os.path.exists(log_file):
        open(log_file, 'w').close()

    while True:
        try:
            current_size = os.path.getsize(log_file)

            if current_size > last_size:
                with open(log_file, 'r') as f:
                    f.seek(last_size)
                    new_lines = f.read()

                    if new_lines:
                        for line in new_lines.split('\n'):
                            if line.strip():
                                socketio.emit('new_log', {'data': line})

                    last_size = f.tell()

            time.sleep(1)

        except Exception as e:
            print(f"Log monitoring error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=monitor_logs, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)