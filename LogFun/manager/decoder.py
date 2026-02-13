import json
import os
from .storage import get_storage
from .config import get_config


class LogDecoder:
    def __init__(self, app_name=None, custom_config=None):
        self.app_name = app_name
        self.storage = get_storage()

        # Support loading config from storage OR directly passed (for offline decode)
        if custom_config:
            self.config = custom_config
            self.log_path = None  # No file path for custom config mode
        else:
            self.config = self.storage.get_app_config(app_name)
            self.log_path = self.storage._get_log_path(app_name)

        self.func_map = {}
        self.tpl_map = {}
        self._build_maps()

    def _build_maps(self):
        if not self.config or "functions" not in self.config:
            return

        for fid, func in self.config["functions"].items():
            self.func_map[str(fid)] = func.get("name", f"Func<{fid}>")
            if "templates" in func:
                for tid, tpl in func["templates"].items():
                    self.tpl_map[str(tid)] = tpl.get("content", f"Tpl<{tid}>")

    def _parse_line(self, line):
        """
        Robust parser for: TS AppID FuncID Dur LogJSON VarsJSON
        """
        try:
            line = line.strip()
            if not line: return None

            parts = line.split(' ', 4)
            if len(parts) < 5: return None

            ts, app_id, func_id, duration, rest = parts

            # Robust JSON decoding
            decoder = json.JSONDecoder()
            try:
                log_data, idx = decoder.raw_decode(rest)
                vars_str = rest[idx:].lstrip()
                variables, _ = decoder.raw_decode(vars_str)
            except:
                # Fallback: maybe split by known separator if JSON fails?
                # For now return None to skip malformed lines
                return None

            return {"ts": ts, "fid": str(func_id), "dur": duration, "data": log_data, "vars": variables}
        except Exception:
            return None

    def decode_line_to_text(self, parsed):
        if not parsed: return []

        results = []
        func_name = self.func_map.get(parsed["fid"], f"Func<{parsed['fid']}>")
        ts = parsed["ts"]
        vars_iter = iter(parsed["vars"])

        for entry in parsed["data"]:
            if len(entry) < 2: continue
            lvl, tid = entry[0], str(entry[1])
            tpl_content = self.tpl_map.get(tid, f"Unresolved<{tid}>")

            needed_vars = tpl_content.count("%s")
            current_vars = []
            try:
                for _ in range(needed_vars):
                    current_vars.append(next(vars_iter))
            except StopIteration:
                pass

            try:
                msg = tpl_content % tuple(current_vars) if current_vars else tpl_content
            except:
                msg = f"{tpl_content} [Vars Error: {current_vars}]"

            results.append(f"{ts} [{lvl}] [{func_name}] {msg}")

        return results

    def search_logs(self, search_type, keyword, limit=1000):
        if not self.log_path or not os.path.exists(self.log_path): return []

        results = []
        keyword = keyword.lower().strip()

        target_fids = set()
        target_tids = set()

        # Pre-filter maps
        if search_type == 'function':
            for fid, name in self.func_map.items():
                if keyword in name.lower(): target_fids.add(fid)
            if not target_fids: return []
        elif search_type == 'template':
            for tid, content in self.tpl_map.items():
                if keyword in content.lower(): target_tids.add(tid)
            if not target_tids: return []

        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Quick skip for variable search
                    if search_type == 'variable' and keyword not in line.lower(): continue

                    parsed = self._parse_line(line)
                    if not parsed: continue

                    match = False
                    if search_type == 'function':
                        if parsed["fid"] in target_fids: match = True
                    elif search_type == 'template':
                        for entry in parsed["data"]:
                            if str(entry[1]) in target_tids:
                                match = True
                                break
                    elif search_type == 'variable':
                        # Double check JSON decoded vars
                        for v in parsed["vars"]:
                            if keyword in str(v).lower():
                                match = True
                                break

                    if match:
                        results.extend(self.decode_line_to_text(parsed))
                        if len(results) >= limit: break
        except:
            pass
        return results

    def decode_all_generator(self):
        if not self.log_path or not os.path.exists(self.log_path): return
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                parsed = self._parse_line(line)
                if parsed:
                    for txt in self.decode_line_to_text(parsed):
                        yield txt + "\n"

    def decode_offline_files(self, log_content_str):
        """
        Decodes a raw log string using the config loaded in __init__.
        Used for uploaded files. Returns a big string (limit size in prod).
        """
        output = []
        lines = log_content_str.splitlines()
        for line in lines:
            parsed = self._parse_line(line)
            if parsed:
                decoded = self.decode_line_to_text(parsed)
                output.extend(decoded)
            else:
                # keep plain lines if they are not compressed logs (e.g. exceptions)
                output.append(line)
        return "\n".join(output)
