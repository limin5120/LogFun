import socketserver
import json
import threading
import time
import ast
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
                        # 1. Sync Agent config into Server (Preserve server-side rules)
                        if "config" in data:
                            storage.sync_config(app_name, data["config"])
                        if "blocked_stats" in data:
                            if hasattr(storage, 'update_stats'):
                                storage.update_stats(app_name, data["blocked_stats"])

                        # [FIX 1] Immediately push back the authoritative config to Agent.
                        # This ensures Agent gets existing mute rules right at startup.
                        full_config = storage.get_app_config(app_name)
                        resp = {"timestamp": time.time(), "config": full_config}
                        # We use TYPE_HEARTBEAT because Agent listens for 'config' in this packet type
                        self.request.sendall(pack_packet(TYPE_HEARTBEAT, json.dumps(resp).encode('utf-8')))

                elif p_type == TYPE_LOG_DATA:
                    raw_input = data.get("log", "")
                    log_type = data.get("type", "compress")

                    logs = raw_input if isinstance(raw_input, list) else [raw_input]

                    for raw_log in logs:
                        monitor.tick()
                        if app_name != "unknown":
                            write_content = str(raw_log)
                            if log_type == "normal":
                                try:
                                    log_obj = json.loads(raw_log)
                                    write_content = f"{log_obj.get('ts')} [{log_obj.get('name')}] {log_obj.get('lvl')}: {log_obj.get('msg')}"
                                    if "fid" in log_obj and get_config().algo_config.get("enable", True):
                                        balancer.record_traffic(app_name, int(log_obj["fid"]))
                                except:
                                    pass
                            elif log_type == "compress":
                                try:
                                    parts = raw_log.split('|')
                                    fid = int(parts[1])
                                    if get_config().algo_config.get("enable", True):
                                        balancer.record_traffic(app_name, fid)
                                except:
                                    pass

                            storage.write_log(app_name, write_content, log_type)

                elif p_type == TYPE_HEARTBEAT:
                    if app_name != "unknown":
                        if "blocked_stats" in data and hasattr(storage, 'update_stats'):
                            storage.update_stats(app_name, data["blocked_stats"])

                        balancer.run_analysis_cycle(app_name)
                        full_config = storage.get_app_config(app_name)
                        resp = {"timestamp": time.time(), "config": full_config}
                        self.request.sendall(pack_packet(TYPE_HEARTBEAT, json.dumps(resp).encode('utf-8')))

        except Exception as e:
            print(f"[Manager] Error: {e}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


def start_server():
    cfg = get_config()
    server = ThreadedTCPServer((cfg.get("server", "host"), cfg.get("server", "port")), LogRequestHandler)
    threading.Thread(target=run_web_server, args=(9998, ), daemon=True).start()
    print(f"[Manager] Listening on {cfg.get('server', 'host')}:{cfg.get('server', 'port')}")
    server.serve_forever()


if __name__ == "__main__": start_server()
