import socketserver
import json
import threading
import time
from .config import get_config
from .protocol import unpack_packet, pack_packet, TYPE_HANDSHAKE, TYPE_LOG_DATA, TYPE_HEARTBEAT
from .storage import get_storage
from .balancer import get_balancer
from .stats import get_monitor
from .web import run_web_server


class LogRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        addr = self.client_address
        app_name = "unknown"
        storage = get_storage()
        balancer = get_balancer()
        monitor = get_monitor()

        try:
            while True:
                p_type, body = unpack_packet(self.request)
                if p_type is None: break
                try:
                    data = json.loads(body.decode('utf-8'))
                except:
                    continue

                if p_type == TYPE_HANDSHAKE:
                    app_name = data.get("app_name", "unknown")
                    if app_name != "unknown":
                        if "config" in data: storage.sync_config(app_name, data["config"])
                        if "blocked_stats" in data: storage.update_stats(app_name, data["blocked_stats"])

                        full_config = storage.get_app_config(app_name)
                        resp = {"timestamp": time.time(), "config": full_config}
                        self.request.sendall(pack_packet(TYPE_HEARTBEAT, json.dumps(resp).encode('utf-8')))

                elif p_type == TYPE_LOG_DATA:
                    raw_input = data.get("log", "")
                    log_type = data.get("type", "compress")
                    logs = raw_input if isinstance(raw_input, list) else [raw_input]

                    # IMPORTANT: If app_name is still unknown, we shouldn't record balancer traffic
                    # Handshake usually arrives first, but we handle it defensively
                    for raw_log in logs:
                        monitor.tick()
                        if app_name == "unknown": continue

                        write_content = str(raw_log)
                        if log_type == "normal":
                            try:
                                log_obj = json.loads(raw_log)
                                if "fid" in log_obj and get_config().algo_config.get("enable", True):
                                    balancer.record_traffic(app_name, int(log_obj["fid"]))
                            except:
                                pass
                        elif log_type == "compress":
                            try:
                                parts = raw_log.split(' ', 5)
                                if len(parts) >= 6:
                                    fid = int(parts[2])
                                    vars_list = []
                                    if get_config().algo_config.get("active") == "weighted_entropy":
                                        # Correct JSON extraction
                                        decoder = json.JSONDecoder()
                                        _, idx = decoder.raw_decode(parts[4])
                                        vars_str = parts[4][idx:].lstrip()
                                        vars_list, _ = decoder.raw_decode(vars_str)

                                    if get_config().algo_config.get("enable", True):
                                        balancer.record_traffic(app_name, fid, vars_list)
                            except:
                                pass

                        storage.write_log(app_name, write_content, log_type)

                elif p_type == TYPE_HEARTBEAT:
                    if "app_name" in data: app_name = data["app_name"]
                    if app_name != "unknown":
                        if "blocked_stats" in data: storage.update_stats(app_name, data["blocked_stats"])
                        balancer.run_analysis_cycle(app_name)
                        full_config = storage.get_app_config(app_name)
                        resp = {"timestamp": time.time(), "config": full_config}
                        self.request.sendall(pack_packet(TYPE_HEARTBEAT, json.dumps(resp).encode('utf-8')))
        except Exception as e:
            print(f"[Manager] Handler error from {addr}: {e}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def start_server():
    cfg = get_config()
    server = ThreadedTCPServer((cfg.get("server", "host"), cfg.get("server", "port")), LogRequestHandler)
    threading.Thread(target=run_web_server, args=(9998, ), daemon=True).start()
    print(f"[Manager] Listening on {cfg.get('server', 'host')}:{cfg.get('server', 'port')}")
    server.serve_forever()


if __name__ == "__main__": start_server()
