import threading
from .config import get_config, LogMode
from .net import get_network_client


class Agent:
    def __init__(self):
        self.config = get_config()
        self.net_client = get_network_client()
        self.file_lock = threading.Lock()

    def log(self, payload, log_type="compress"):
        """
        Dispatch log payload based on current mode.
        Args:
            payload: string or json string
            log_type: "compress" or "normal" (Required for proper server-side parsing)
        """
        mode = self.config.mode

        if mode == LogMode.DEV:
            print(payload)

        elif mode == LogMode.FILE:
            with self.file_lock:
                try:
                    with open(self.config.log_file_path, "a", encoding="utf-8") as f:
                        f.write(str(payload) + "\n")
                except Exception:
                    pass

        elif mode == LogMode.REMOTE:
            # Pass the log_type explicitly to the network client
            self.net_client.send_log(payload, log_type=log_type)


_agent = Agent()


def get_agent():
    return _agent
