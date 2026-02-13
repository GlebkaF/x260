#!/usr/bin/env python3
"""Minimal overview server: one page with CPU, RAM, disk, load. Stdlib only."""
import html
import http.server
import os
import re
PORT = 61208
BIND = "0.0.0.0"


def read_proc(path):
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return ""


def get_load():
    s = read_proc("/proc/loadavg")
    if not s:
        return None
    parts = s.split()
    return {"load1": parts[0], "load5": parts[1], "load15": parts[2]} if len(parts) >= 3 else None


def get_cpu():
    raw = read_proc("/proc/stat")
    if not raw:
        return None
    m = re.search(r"^cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", raw, re.M)
    if not m:
        return None
    user, nice, system, idle, iowait, irq, softirq = map(int, m.groups())
    total = user + nice + system + idle + iowait + irq + softirq
    used = total - idle
    return round(100.0 * used / total, 1) if total else 0


def get_mem():
    raw = read_proc("/proc/meminfo")
    if not raw:
        return None
    def g(k):
        m = re.search(rf"^{k}:\s+(\d+)", raw, re.M)
        return int(m.group(1)) * 1024 if m else 0
    total = g("MemTotal")
    avail = g("MemAvailable")
    if not total:
        return None
    used = total - avail
    return {"used_mb": round(used / 1024 / 1024, 1), "total_mb": round(total / 1024 / 1024, 1), "pct": round(100.0 * used / total, 1)}


def get_disk():
    raw = read_proc("/proc/mounts")
    if not raw:
        return None
    root = None
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "/":
            root = parts[0]
            break
    if not root:
        return None
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        return {"used_gb": round(used / 1024**3, 1), "total_gb": round(total / 1024**3, 1), "pct": round(100.0 * used / total, 1)}
    except Exception:
        return None


def get_uptime():
    s = read_proc("/proc/uptime")
    if not s:
        return None
    try:
        sec = float(s.split()[0])
        d, rest = divmod(int(sec), 86400)
        h, rest = divmod(rest, 3600)
        m, _ = divmod(rest, 60)
        if d:
            return f"{d}d {h}h"
        if h:
            return f"{h}h {m}m"
        return f"{m}m"
    except Exception:
        return None


def collect():
    load = get_load()
    cpu = get_cpu()
    mem = get_mem()
    disk = get_disk()
    uptime = get_uptime()
    return {
        "load": load,
        "cpu": cpu,
        "mem": mem,
        "disk": disk,
        "uptime": uptime,
    }


def html_page(data):
    def v(x, default="—"):
        return x if x is not None else default
    load = data.get("load") or {}
    cpu = data.get("cpu")
    mem = data.get("mem") or {}
    disk = data.get("disk") or {}
    uptime = data.get("uptime")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>x260 overview</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui,sans-serif; margin: 0; padding: 1rem; background: #0d1117; color: #e6edf3; }}
    h1 {{ font-size: 1.1rem; margin: 0 0 1rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem; max-width: 640px; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; }}
    .card h2 {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: .05em; color: #8b949e; margin: 0 0 0.5rem; }}
    .card .val {{ font-size: 1.4rem; font-weight: 600; }}
    .card .sub {{ font-size: 0.75rem; color: #8b949e; margin-top: 0.25rem; }}
    .foot {{ margin-top: 1rem; font-size: 0.75rem; color: #8b949e; }}
  </style>
  <meta http-equiv="refresh" content="3">
</head>
<body>
  <h1>x260</h1>
  <div class="grid">
    <div class="card"><h2>CPU</h2><div class="val">{v(cpu)}%</div></div>
    <div class="card"><h2>Load (1m)</h2><div class="val">{v(load.get('load1'))}</div></div>
    <div class="card"><h2>RAM</h2><div class="val">{v(mem.get('pct'))}%</div><div class="sub">{v(mem.get('used_mb'))} / {v(mem.get('total_mb'))} MiB</div></div>
    <div class="card"><h2>Disk /</h2><div class="val">{v(disk.get('pct'))}%</div><div class="sub">{v(disk.get('used_gb'))} / {v(disk.get('total_gb'))} GiB</div></div>
    <div class="card"><h2>Uptime</h2><div class="val">{v(uptime)}</div></div>
  </div>
  <p class="foot">Refresh every 3s</p>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/" and self.path != "/index.html":
            self.send_error(404)
            return
        data = collect()
        body = html_page(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def main():
    server = http.server.HTTPServer((BIND, PORT), Handler)
    print(f"Overview at http://{BIND}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
