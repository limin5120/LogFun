import logging
from flask import Flask, jsonify, request, render_template
from .stats import get_monitor
from .balancer import get_balancer
from .config import get_config
from .storage import get_storage

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__, template_folder='templates')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    return jsonify(get_monitor().get_snapshot())


@app.route('/api/balancer')
def api_balancer():
    cfg = get_config().algo_config
    active = cfg.get("active", "zscore")
    params = cfg.get(active, {})
    return jsonify({"active_strategy": active, "params": params})


@app.route('/api/registry')
def api_registry():
    app_name = request.args.get('app', 'root')
    storage = get_storage()

    # Get Config Tree
    config = storage.get_app_config(app_name)

    # [FIX] Get Runtime Stats (Blocked Counts)
    stats = storage.get_app_stats(app_name)

    # Merge stats into config for easier frontend consumption
    if config and "functions" in config:
        for fid, func in config["functions"].items():
            # Inject blocked count for function
            func["_blocked"] = stats.get(fid, 0)

            # Inject blocked count for templates
            if "templates" in func:
                for tid, tpl in func["templates"].items():
                    stats_key = f"{fid}:{tid}"
                    tpl["_blocked"] = stats.get(stats_key, 0)

    return jsonify(config)


@app.route('/api/control', methods=['POST'])
def api_control():
    d = request.json
    enable = (d.get('action') == 'unmute')
    get_storage().update_control(d.get('app', 'root'), d.get('id'), d.get('sub_id'), enable)
    return jsonify({"status": "ok"})


def run_web_server(port=9998):
    app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)
