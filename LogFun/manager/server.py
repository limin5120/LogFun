import socketserver
import json
import threading
import time
import ast
from .config import get_config
from .protocol import unpack_packet, pack_packet, TYPE_HANDSHAKE, TYPE_LOG_DATA, TYPE_HEARTBEAT
from .storage import get_storage
from .balancer import get_balancer
from .stats import get_monitor  # [NEW]
from .web import run_web_server  # [NEW]


class LogRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        addr = self.client_address
        app_name = "unknown"
        storage = get_storage()
        balancer = get_balancer()
        monitor = get_monitor()  # [NEW]
        config = get_config()

        try:
            while True:
                p_type, body = unpack_packet(self.request)
                if p_type is None:
                    break

                try:
                    data = json.loads(body.decode('utf-8'))
                except:
                    continue

                if p_type == TYPE_HANDSHAKE:
                    app_name = data.get("app_name", "unknown")
                    client_tpls = data.get("templates", {})
                    client_funcs = data.get("functions", {})
                    storage.sync_registry(app_name, client_funcs, client_tpls)

                elif p_type == TYPE_LOG_DATA:
                    raw_log = data.get("log", "")
                    log_type = data.get("type", "compress")

                    # [NEW] Update Traffic Stats
                    monitor.tick()

                    if app_name != "unknown":
                        func_id = 0
                        variables = []
                        final_log_str = raw_log

                        if log_type == "compress":
                            try:
                                parts = raw_log.split('|')
                                if len(parts) >= 5:
                                    func_id = int(parts[1])
                                    vars_str = parts[4]
                                    try:
                                        variables = ast.literal_eval(vars_str)
                                    except:
                                        variables = []
                            except:
                                pass

                        elif log_type == "normal":
                            try:
                                log_obj = json.loads(raw_log)
                                if isinstance(log_obj, dict) and "fid" in log_obj:
                                    func_id = int(log_obj.get("fid", 0))
                                    final_log_str = f"{log_obj['ts']} [{log_obj['name']}] {log_obj['lvl']}: {log_obj['msg']}"
                            except:
                                pass

                        storage.write_log(app_name, final_log_str, log_type)

                        if config.algo_config.get("enable", True):
                            if func_id > 0:
                                balancer.record_traffic(app_name, func_id, variables)

                elif p_type == TYPE_HEARTBEAT:
                    mute_ids = []
                    if config.algo_config.get("enable", True):
                        mute_ids = balancer.analyze(app_name)

                    # [TODO] We can update monitor with active mute_ids here for the dashboard

                    response = {
                        "timestamp": time.time(),
                        "mute_list": mute_ids,
                    }
                    self.request.sendall(pack_packet(TYPE_HEARTBEAT, json.dumps(response).encode('utf-8')))

        except Exception as e:
            print(f"[Manager] Error handling client {addr}: {e}")
        finally:
            pass


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def start_server():
    config = get_config()
    host = config.get("server", "host")
    port = config.get("server", "port")

    server = ThreadedTCPServer((host, port), LogRequestHandler)

    def config_watcher():
        while True:
            if config.reload():
                pass
            time.sleep(5)

    # 1. Start Config Watcher
    t_cfg = threading.Thread(target=config_watcher, daemon=True)
    t_cfg.start()

    # 2. Start Web Dashboard [NEW]
    print(f"[Manager] Dashboard running on http://{host}:9998")
    t_web = threading.Thread(target=run_web_server, args=(9998, ), daemon=True)
    t_web.start()

    print(f"[Manager] TCP Server listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    start_server()
