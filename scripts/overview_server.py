#!/usr/bin/env python3
"""Minimal overview server: one page with CPU, RAM, disk, load + history charts. Stdlib only."""
import html
import http.server
import json
import os
import re
import time
import threading
from collections import deque

PORT = 61208
BIND = "0.0.0.0"
HISTORY_INTERVAL = 30  # seconds between samples
HISTORY_MAX_POINTS = 2880  # 24h at 30s
_history = deque(maxlen=HISTORY_MAX_POINTS)
_history_lock = threading.Lock()


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
    if len(parts) < 3:
        return None
    try:
        return {"load1": float(parts[0]), "load5": float(parts[1]), "load15": float(parts[2])}
    except ValueError:
        return None


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


def get_cpu_delta():
    """CPU % over last second (two reads)."""
    r1 = read_proc("/proc/stat")
    if not r1:
        return None
    m1 = re.search(r"^cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", r1, re.M)
    if not m1:
        return None
    time.sleep(1)
    r2 = read_proc("/proc/stat")
    if not r2:
        return None
    m2 = re.search(r"^cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", r2, re.M)
    if not m2:
        return None
    idles = [int(m1.group(4)), int(m2.group(4))]
    totals = [sum(map(int, m1.groups())), sum(map(int, m2.groups()))]
    d_idle = idles[1] - idles[0]
    d_total = totals[1] - totals[0]
    if d_total <= 0:
        return None
    return round(100.0 * (1 - d_idle / d_total), 1)


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


def collector_loop():
    """Background: every HISTORY_INTERVAL sec append one sample to history."""
    while True:
        time.sleep(HISTORY_INTERVAL)
        try:
            cpu = get_cpu_delta()
            if cpu is None:
                cpu = get_cpu()
            mem = get_mem()
            disk = get_disk()
            load = get_load()
            load1 = load.get("load1") if load else None
            with _history_lock:
                _history.append({
                    "ts": int(time.time()),
                    "cpu": cpu,
                    "mem_pct": mem.get("pct") if mem else None,
                    "disk_pct": disk.get("pct") if disk else None,
                    "load1": load1,
                })
        except Exception:
            pass


def history_json(period):
    """period in seconds; return last N points."""
    n = max(1, min(HISTORY_MAX_POINTS, period // HISTORY_INTERVAL))
    with _history_lock:
        points = list(_history)[-n:]
    if not points:
        return {"labels": [], "cpu": [], "mem": [], "disk": [], "load": []}
    labels = [p["ts"] for p in points]
    return {
        "labels": labels,
        "cpu": [p["cpu"] for p in points],
        "mem": [p["mem_pct"] for p in points],
        "disk": [p["disk_pct"] for p in points],
        "load": [p["load1"] for p in points],
    }


def html_page(data):
    def v(x, default="—"):
        return x if x is not None else default
    opts = "{ hour: '2-digit', minute: '2-digit' }"
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
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui,sans-serif; margin: 0; padding: 1rem; background: #0d1117; color: #e6edf3; }}
    h1 {{ font-size: 1.1rem; margin: 0 0 1rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem; max-width: 640px; }}
    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; }}
    .card h2 {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: .05em; color: #8b949e; margin: 0 0 0.5rem; }}
    .card .val {{ font-size: 1.4rem; font-weight: 600; }}
    .card .sub {{ font-size: 0.75rem; color: #8b949e; margin-top: 0.25rem; }}
    .charts {{ margin-top: 1.5rem; max-width: 900px; }}
    .chart-box {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }}
    .chart-box h2 {{ font-size: 0.85rem; margin: 0 0 0.5rem; color: #8b949e; }}
    .period {{ margin-bottom: 0.5rem; }}
    .period select {{ background: #21262d; color: #e6edf3; border: 1px solid #30363d; padding: 0.25rem 0.5rem; border-radius: 4px; }}
    .foot {{ margin-top: 1rem; font-size: 0.75rem; color: #8b949e; }}
  </style>
  <meta http-equiv="refresh" content="10">
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
  <div class="charts">
    <div class="chart-box">
      <h2>History</h2>
      <div class="period">
        <label>Period: </label>
        <select id="period">
          <option value="3600">Last 1 hour</option>
          <option value="21600" selected>Last 6 hours</option>
          <option value="86400">Last 24 hours</option>
        </select>
      </div>
      <canvas id="chart" height="220"></canvas>
    </div>
  </div>
  <p class="foot">Page refresh 10s · History every 30s</p>
  <script>
    const ctx = document.getElementById('chart').getContext('2d');
    let chart = null;
    function fmtTime(ts) {{ return new Date(ts*1000).toLocaleTimeString([], {opts}); }}
    function loadHistory(period) {{
      fetch('/api/history?period=' + period).then(r => r.json()).then(data => {{
        const labels = (data.labels || []).map(fmtTime);
        const datasets = [
          {{ label: 'CPU %', data: data.cpu || [], borderColor: '#58a6ff', tension: 0.2, fill: false }},
          {{ label: 'RAM %', data: data.mem || [], borderColor: '#3fb950', tension: 0.2, fill: false }},
          {{ label: 'Disk %', data: data.disk || [], borderColor: '#d29922', tension: 0.2, fill: false }},
          {{ label: 'Load 1m', data: data.load || [], borderColor: '#bc8cff', tension: 0.2, fill: false, yAxisID: 'y1' }}
        ];
        if (chart) chart.destroy();
        chart = new Chart(ctx, {{
          type: 'line',
          data: {{ labels, datasets }},
          options: {{
            responsive: true,
            plugins: {{ legend: {{ position: 'top' }} }},
            scales: {{
              y: {{ min: 0, max: 100, title: {{ display: true, text: '%' }} }},
              y1: {{ position: 'right', min: 0, grid: {{ drawOnChartArea: false }}, title: {{ display: true, text: 'Load' }} }}
            }}
          }}
        }});
      }});
    }}
    document.getElementById('period').addEventListener('change', function() {{ loadHistory(this.value); }});
    loadHistory(21600);
  </script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if "?" in self.path:
            path, qs = self.path.split("?", 1)
        else:
            path, qs = self.path, ""
        if path == "/api/history":
            period = 21600
            for part in qs.split("&"):
                if part.startswith("period="):
                    try:
                        period = int(part.split("=", 1)[1])
                    except ValueError:
                        pass
                    break
            data = history_json(period)
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path != "/" and path != "/index.html":
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
    t = threading.Thread(target=collector_loop, daemon=True)
    t.start()
    server = http.server.HTTPServer((BIND, PORT), Handler)
    print(f"Overview at http://{BIND}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
