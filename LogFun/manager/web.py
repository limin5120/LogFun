import os
from flask import Flask, jsonify, request, render_template
from .stats import get_monitor
from .balancer import get_balancer
from .config import get_config
from .storage import get_storage

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
app = Flask(__name__, template_folder=template_dir)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    return jsonify(get_monitor().get_snapshot())


@app.route('/api/registry')
def api_registry():
    app_name = request.args.get('app', 'root')
    return jsonify(get_storage().get_all_registries(app_name))


@app.route('/api/control', methods=['POST'])
def api_control():
    data = request.json
    # Logic to manually mute/unmute could be implemented here
    print(f"[WebControl] Action received: {data}")
    return jsonify({"status": "received"})


def run_web_server(port=9998):
    app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)
