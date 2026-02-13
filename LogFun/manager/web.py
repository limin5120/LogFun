import logging
import json
from flask import Flask, jsonify, request, render_template, Response, stream_with_context
from .stats import get_monitor
from .balancer import get_balancer
from .config import get_config
from .storage import get_storage
from .decoder import LogDecoder

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


# [FIX] New endpoint for app list
@app.route('/api/apps')
def api_apps():
    return jsonify(get_storage().get_all_apps())


@app.route('/api/registry')
def api_registry():
    app_name = request.args.get('app', 'root')
    storage = get_storage()
    config = storage.get_app_config(app_name)
    stats = storage.get_app_stats(app_name)

    if config and "functions" in config:
        for fid, func in config["functions"].items():
            if func.get("enabled", True): func["_blocked"] = 0
            else: func["_blocked"] = stats.get(fid, 0)
            if "templates" in func:
                for tid, tpl in func["templates"].items():
                    stats_key = f"{fid}:{tid}"
                    if tpl.get("enabled", True): tpl["_blocked"] = 0
                    else: tpl["_blocked"] = stats.get(stats_key, 0)
    return jsonify(config)


@app.route('/api/control', methods=['POST'])
def api_control():
    d = request.json
    enable = (d.get('action') == 'unmute')
    get_storage().update_control(d.get('app', 'root'), d.get('id'), d.get('sub_id'), enable, source="manual")
    return jsonify({"status": "ok"})


@app.route('/api/search')
def api_search():
    app_name = request.args.get('app', '')
    s_type = request.args.get('type', 'function')
    keyword = request.args.get('kw', '')
    if not app_name or not keyword: return jsonify([])

    decoder = LogDecoder(app_name)
    return jsonify(decoder.search_logs(s_type, keyword, limit=500))


@app.route('/api/download')
def api_download():
    app_name = request.args.get('app', '')
    if not app_name: return "App Name Missing", 400
    decoder = LogDecoder(app_name)
    return Response(stream_with_context(decoder.decode_all_generator()), mimetype="text/plain", headers={"Content-Disposition": f"attachment;filename={app_name}_decoded.txt"})


@app.route('/api/upload', methods=['POST'])
def api_upload():
    try:
        f_log = request.files.get('file_log')
        f_conf = request.files.get('file_config')
        if not f_log or not f_conf:
            return jsonify({"error": "Both .log and .json files are required"}), 400

        log_content = f_log.read().decode('utf-8', errors='ignore')
        conf_content = f_conf.read().decode('utf-8', errors='ignore')
        try:
            config_json = json.loads(conf_content)
        except:
            return jsonify({"error": "Invalid JSON Config file"}), 400

        decoder = LogDecoder(custom_config=config_json)
        decoded_text = decoder.decode_offline_files(log_content)
        return jsonify({"status": "ok", "content": decoded_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_web_server(port=9998):
    app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)
