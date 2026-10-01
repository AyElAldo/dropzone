#!/usr/bin/env python3
"""
dropzone.py — Servidor HTTP ligero para transferencia de archivos (pentest/CTF)
Corre en Parrot/Kali, cualquier navegador de la red puede subir archivos.

Uso:
  python3 dropzone.py              # puerto 8080, guarda en ./uploads/
  python3 dropzone.py 9090         # puerto custom
  python3 dropzone.py 9090 /tmp    # puerto + directorio custom
"""

import cgi, html, json, mimetypes, os, sys, socket
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────
PORT       = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
UPLOAD_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else "uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Utilidades ────────────────────────────────────────────────────────────────
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def fmt_size(b):
    for unit in ("B","KB","MB","GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.2f} TB"

# ── Página HTML embebida ───────────────────────────────────────────────────────
HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>dropzone</title>
<style>
  :root {
    --bg:      #0d1117;
    --surface: #161b22;
    --border:  #30363d;
    --text:    #c9d1d9;
    --muted:   #6e7681;
    --accent:  #58a6ff;
    --ok:      #3fb950;
    --err:     #f85149;
    --font:    ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    font-size: 14px;
    line-height: 1.55;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    padding: 3rem 1rem;
  }

  /* ── Ventana de terminal ── */
  .window {
    width: 100%;
    max-width: 680px;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
    background: var(--surface);
    height: fit-content;
  }

  .titlebar {
    display: flex;
    align-items: center;
    gap: .7rem;
    padding: .6rem .9rem;
    background: #0d1117;
    border-bottom: 1px solid var(--border);
  }
  .dots { display: flex; gap: .4rem; }
  .dot  { width: 11px; height: 11px; border-radius: 50%; }
  .dot.r { background: #ff5f56; }
  .dot.y { background: #ffbd2e; }
  .dot.g { background: #27c93f; }
  .title { flex: 1; text-align: center; color: var(--muted); font-size: .78rem; }

  .content { padding: 1.5rem 1.5rem 1.3rem; }

  .prompt { color: var(--muted); font-size: .8rem; margin-bottom: .9rem; }
  .prompt b { color: var(--accent); font-weight: 600; }

  .status {
    display: flex; align-items: center; gap: .4rem;
    font-size: .72rem; color: var(--muted);
    margin-bottom: 1.4rem;
  }
  .status .cursor {
    display: inline-block; width: 7px; height: 13px;
    background: var(--ok);
    animation: blink 1s step-start infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }

  /* ── Zona de carga ── */
  .dropzone {
    border: 1px dashed var(--border);
    border-radius: 4px;
    padding: 2.2rem 1rem;
    text-align: center;
    cursor: pointer;
    position: relative;
    transition: border-color .15s, background-color .15s;
  }
  .dropzone:hover, .dropzone.over {
    border-color: var(--accent);
    background: rgba(88,166,255,.06);
  }
  .dropzone input {
    position: absolute; inset: 0;
    opacity: 0; cursor: pointer;
  }
  .dz-label { color: var(--text); font-size: .85rem; margin-bottom: .35rem; }
  .dz-sub   { color: var(--muted); font-size: .72rem; }

  /* ── Cola de subida ── */
  #queue { display: flex; flex-direction: column; gap: .5rem; margin-top: 1rem; }
  .q-item {
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: .55rem .75rem;
    background: var(--bg);
  }
  .q-head {
    display: flex; justify-content: space-between;
    font-size: .78rem; margin-bottom: .4rem;
  }
  .q-name { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; }
  .q-st   { color: var(--muted); font-size: .72rem; }
  .q-st.ok  { color: var(--ok); }
  .q-st.err { color: var(--err); }

  .track { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; }
  .fill  { height: 100%; width: 0%; background: var(--accent); transition: width .1s linear; }
  .fill.ok  { background: var(--ok); }
  .fill.err { background: var(--err); }

  /* ── Encabezado de sección ── */
  .section {
    display: flex; justify-content: space-between; align-items: center;
    margin: 2rem 0 .8rem;
    padding-bottom: .4rem;
    border-bottom: 1px solid var(--border);
    font-size: .78rem; color: var(--muted);
  }
  .refresh-btn {
    background: none; border: 1px solid var(--border); border-radius: 4px;
    color: var(--muted); cursor: pointer;
    font-family: var(--font); font-size: .72rem;
    padding: .2rem .6rem;
    transition: border-color .15s, color .15s;
  }
  .refresh-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* ── Listado de archivos ── */
  #file-list { display: flex; flex-direction: column; gap: .35rem; }
  .fentry {
    display: flex; justify-content: space-between; align-items: center;
    padding: .5rem .75rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: .78rem;
    background: var(--bg);
  }
  .fentry a {
    color: var(--accent); text-decoration: none;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 55%;
  }
  .fentry a:hover { text-decoration: underline; }
  .fmeta { color: var(--muted); font-size: .7rem; text-align: right; }
  .empty {
    text-align: center; color: var(--muted);
    padding: 1.4rem; font-size: .78rem;
    border: 1px dashed var(--border); border-radius: 4px;
  }

  footer {
    margin-top: 1.6rem; padding-top: 1rem;
    border-top: 1px solid var(--border);
    font-size: .68rem; color: var(--muted);
  }
  footer .warn { color: var(--err); }
</style>
</head>
<body>

<div class="window">
  <div class="titlebar">
    <div class="dots"><span class="dot r"></span><span class="dot y"></span><span class="dot g"></span></div>
    <div class="title">dropzone — <span id="host-tag">—</span></div>
  </div>

  <div class="content">
    <div class="prompt"><b>$</b> dropzone --serve <span id="clock-tag">--:--:--</span></div>
    <div class="status"><span class="cursor"></span>&nbsp;sistema activo</div>

    <div class="dropzone" id="dz">
      <input type="file" id="fi" multiple accept="*/*">
      <div class="dz-label">arrastra archivos aquí o haz clic para seleccionar</div>
      <div class="dz-sub">cualquier tipo · múltiples archivos soportados</div>
    </div>

    <div id="queue"></div>

    <div class="section">
      <span><b>$</b> ls uploads/</span>
      <button class="refresh-btn" onclick="loadFiles()">refresh</button>
    </div>
    <div id="file-list"><div class="empty">sin transferencias</div></div>

    <footer>
      <span class="warn">[!]</span> canal sin cifrar &nbsp;·&nbsp; uso exclusivo en redes controladas / entornos de laboratorio
    </footer>
  </div>
</div>

<script>
  // Reloj
  function tick() {
    const n = new Date();
    document.getElementById('clock-tag').textContent =
      n.toTimeString().slice(0,8);
  }
  tick(); setInterval(tick, 1000);
  document.getElementById('host-tag').textContent = location.host;

  const dz = document.getElementById('dz');
  const fi = document.getElementById('fi');
  const queueEl = document.getElementById('queue');

  // ── Drag & drop ──────────────────────────────────────────────────────────
  ['dragenter','dragover'].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('over'); }));
  ['dragleave','drop'].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('over'); }));
  dz.addEventListener('drop', e => {
    if (e.dataTransfer.files.length) upload(e.dataTransfer.files);
  });
  fi.addEventListener('change', () => { if (fi.files.length) upload(fi.files); fi.value=''; });

  // ── Formato tamaño ────────────────────────────────────────────────────────
  function fmtSize(b) {
    const u = ['B','KB','MB','GB'];
    let i = 0;
    while (b >= 1024 && i < u.length-1) { b /= 1024; i++; }
    return b.toFixed(1) + ' ' + u[i];
  }

  // ── Upload individual con barra de progreso ───────────────────────────────
  function upload(files) {
    Array.from(files).forEach(file => {
      const id = 'q' + Date.now() + Math.random().toString(36).slice(2);
      const item = document.createElement('div');
      item.className = 'q-item';
      item.innerHTML = `
        <div class="q-head">
          <span class="q-name">${htmlEsc(file.name)}</span>
          <span class="q-st" id="st-${id}">init...</span>
        </div>
        <div class="track"><div class="fill" id="fl-${id}"></div></div>`;
      queueEl.prepend(item);

      const st = document.getElementById('st-' + id);
      const fl = document.getElementById('fl-' + id);
      const fd = new FormData();
      fd.append('file', file);

      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/upload');
      xhr.upload.onprogress = e => {
        if (e.lengthComputable) {
          const p = Math.round(e.loaded / e.total * 100);
          fl.style.width = p + '%';
          st.textContent = p + '%';
        }
      };
      xhr.onload = () => {
        if (xhr.status === 200) {
          fl.style.width = '100%'; fl.classList.add('ok');
          st.textContent = 'ok · ' + fmtSize(file.size); st.classList.add('ok');
          loadFiles();
        } else {
          fl.classList.add('err');
          st.textContent = 'error ' + xhr.status; st.classList.add('err');
        }
      };
      xhr.onerror = () => {
        fl.classList.add('err');
        st.textContent = 'error · timeout'; st.classList.add('err');
      };
      xhr.send(fd);
    });
  }

  function htmlEsc(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Lista de archivos ─────────────────────────────────────────────────────
  function loadFiles() {
    fetch('/files').then(r => r.json()).then(files => {
      const el = document.getElementById('file-list');
      if (!files.length) {
        el.innerHTML = '<div class="empty">sin transferencias</div>'; return;
      }
      el.innerHTML = files.map(f => `
        <div class="fentry">
          <a href="/download/${encodeURIComponent(f.name)}" download="${htmlEsc(f.name)}">${htmlEsc(f.name)}</a>
          <div class="fmeta">${fmtSize(f.size)}<br>${f.time}</div>
        </div>`).join('');
    }).catch(() => {});
  }

  loadFiles();
  setInterval(loadFiles, 5000);
</script>
</body>
</html>"""


# ── Request Handler ───────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] {self.address_string()} → {fmt % args}")

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_body(200, "text/html; charset=utf-8", HTML_PAGE.encode())

        elif self.path == "/files":
            files = []
            for f in sorted(UPLOAD_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file():
                    st = f.stat()
                    files.append({
                        "name": f.name,
                        "size": st.st_size,
                        "time": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
            self._send_body(200, "application/json", json.dumps(files).encode())

        elif self.path.startswith("/download/"):
            fname = self.path[len("/download/"):]
            fpath = UPLOAD_DIR / Path(fname).name          # evita path traversal
            if fpath.exists() and fpath.is_file():
                mime, _ = mimetypes.guess_type(str(fpath))
                data = fpath.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{fpath.name}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404)

    # ── POST ──────────────────────────────────────────────────────────────────
    def do_POST(self):
        if self.path != "/upload":
            self.send_error(404); return

        ct = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ct:
            self.send_error(400, "Expected multipart/form-data"); return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ct}
        )

        saved = []
        items = form["file"] if "file" in form else []
        if not isinstance(items, list):
            items = [items]

        for item in items:
            if not item.filename:
                continue
            safe = Path(item.filename).name        # strip cualquier path
            dest = UPLOAD_DIR / safe
            dest.write_bytes(item.file.read())
            size = dest.stat().st_size
            saved.append({"name": safe, "size": size})
            print(f"  ↑ guardado: {safe} ({fmt_size(size)})")

        self._send_body(200, "application/json", json.dumps({"ok": True, "saved": saved}).encode())

    # ── Helper ────────────────────────────────────────────────────────────────
    def _send_body(self, code, ct, data: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"""
  ╔══════════════════════════════════════╗
  ║         DropZone File Server         ║
  ║             by AyElAldo              ║
  ╠══════════════════════════════════════╣
  ║  Local:    http://localhost:{PORT:<6}  ║
  ║  Red:      http://{ip:<18} ║
  ║  Guardado: {str(UPLOAD_DIR):<28} ║
  ╚══════════════════════════════════════╝
  (Ctrl+C para detener)
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Servidor detenido.")