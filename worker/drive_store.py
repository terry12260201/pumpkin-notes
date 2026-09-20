# -*- coding: utf-8 -*-
"""Google 雲端存放（Pumpkin Notes 素材庫）
用「南瓜本人授權」的方式上傳（OAuth 桌面應用），檔案屬於南瓜的雲端、算公司空間，不吃機器帳號的小配額。
設定都在 ~/.config/pumpkin-notes/config.json：
  google_oauth: {client_id, client_secret, refresh_token}
  drive_folders: {root, html, covers, frames, uploads}
第一次授權：python3 worker/drive_store.py auth   （會開瀏覽器讓南瓜按同意）
"""
import json, os, ssl, sys, time, urllib.request, urllib.parse, mimetypes, re
from pathlib import Path
try:
    import certifi; _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL = ssl.create_default_context()

CFG_PATH = Path(os.path.expanduser("~/.config/pumpkin-notes/config.json"))
SCOPE = "https://www.googleapis.com/auth/drive.file"   # 只能碰「這個 app 建立／被授權的檔案」，夠用且安全
_tok = {"v": "", "exp": 0}

def _cfg():
    return json.loads(CFG_PATH.read_text(encoding="utf-8"))

def _http(method, url, data=None, headers=None, raw=False):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, context=_SSL, timeout=120) as r:
        b = r.read()
    return b if raw else (json.loads(b) if b else {})

def enabled():
    c = _cfg().get("google_oauth") or {}
    return bool(c.get("refresh_token") and c.get("client_id"))

def token():
    if _tok["v"] and time.time() < _tok["exp"] - 60: return _tok["v"]
    c = _cfg()["google_oauth"]
    body = urllib.parse.urlencode({"client_id": c["client_id"], "client_secret": c["client_secret"],
                                   "refresh_token": c["refresh_token"], "grant_type": "refresh_token"}).encode()
    r = _http("POST", "https://oauth2.googleapis.com/token", body, {"Content-Type": "application/x-www-form-urlencoded"})
    _tok["v"] = r["access_token"]; _tok["exp"] = time.time() + int(r.get("expires_in", 3600))
    return _tok["v"]

def _auth_h(extra=None):
    h = {"Authorization": "Bearer " + token()}
    if extra: h.update(extra)
    return h

def find_folder(name, parent):
    q = f"name = '{name.replace(chr(39), chr(92)+chr(39))}' and '{parent}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    r = _http("GET", "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode({"q": q, "fields": "files(id,name)", "pageSize": 5}), headers=_auth_h())
    f = r.get("files") or []
    return f[0]["id"] if f else None

def ensure_folder(name, parent):
    fid = find_folder(name, parent)
    if fid: return fid
    body = json.dumps({"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent]}).encode()
    return _http("POST", "https://www.googleapis.com/drive/v3/files?fields=id", body, _auth_h({"Content-Type": "application/json"}))["id"]

def upload(data: bytes, name: str, parent: str, mime: str = None):
    """上傳一個檔案；同名就覆蓋（先找再更新），回傳 file id。"""
    mime = mime or mimetypes.guess_type(name)[0] or "application/octet-stream"
    q = f"name = '{name.replace(chr(39), chr(92)+chr(39))}' and '{parent}' in parents and trashed = false"
    r = _http("GET", "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode({"q": q, "fields": "files(id)", "pageSize": 1}), headers=_auth_h())
    existing = (r.get("files") or [{}])[0].get("id")
    boundary = "pnb" + str(int(time.time() * 1000))
    meta = {"name": name} if existing else {"name": name, "parents": [parent]}
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta, ensure_ascii=False)}\r\n"
            f"--{boundary}\r\nContent-Type: {mime}\r\n\r\n").encode("utf-8") + data + f"\r\n--{boundary}--".encode()
    h = _auth_h({"Content-Type": f"multipart/related; boundary={boundary}"})
    if existing:
        return _http("PATCH", f"https://www.googleapis.com/upload/drive/v3/files/{existing}?uploadType=multipart&fields=id", body, h)["id"]
    return _http("POST", "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id", body, h)["id"]

def safe_name(s, n=60):
    s = re.sub(r'[\\/:*?"<>|\r\n]+', " ", s).strip()
    return s[:n].rstrip(" .") or "untitled"

def archive_note(date_str: str, title: str, html: bytes = None, cover: bytes = None, images=None, log=print):
    """一篇筆記的雲端歸檔。
    01 報告網頁/<年>/<日期 標題>.html
    02 封面圖/<年>/<日期 標題>.jpg
    03 影片截圖/<年>/<日期 標題>/01.jpg …
    回傳 {html: id, cover: id, folder: id}
    """
    F = _cfg()["drive_folders"]; year = date_str[:4]; base = f"{date_str} {safe_name(title)}"
    out = {}
    if html is not None:
        out["html"] = upload(html, base + ".html", ensure_folder(year, F["html"]), "text/html")
    if cover is not None:
        out["cover"] = upload(cover, base + ".jpg", ensure_folder(year, F["covers"]), "image/jpeg")
    if images:
        fold = ensure_folder(base, ensure_folder(year, F["frames"])); out["folder"] = fold
        for name, data in images:
            upload(data, name, fold, "image/jpeg")
    log(f"☁️ 雲端歸檔完成：{base}（圖 {len(images or [])} 張）")
    return out

# ── 第一次授權（南瓜本人按同意） ─────────────────────────────
def auth_flow():
    import http.server, threading, webbrowser
    c = _cfg().get("google_oauth") or {}
    if not c.get("client_id"): sys.exit("config.json 還沒有 google_oauth.client_id / client_secret")
    port = 8765; redirect = f"http://localhost:{port}/"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent"})
    got = {}
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); got["code"] = q.get("code", [""])[0]
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("<h2>授權完成，可以關掉這個分頁。</h2>".encode()); 
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("localhost", port), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    print("請在瀏覽器打開並按同意：\n" + url)
    try: webbrowser.open(url)
    except Exception: pass
    for _ in range(600):
        if got.get("code"): break
        time.sleep(1)
    if not got.get("code"): sys.exit("沒等到授權")
    body = urllib.parse.urlencode({"code": got["code"], "client_id": c["client_id"], "client_secret": c["client_secret"],
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    r = _http("POST", "https://oauth2.googleapis.com/token", body, {"Content-Type": "application/x-www-form-urlencoded"})
    cfg = _cfg(); cfg["google_oauth"]["refresh_token"] = r["refresh_token"]
    CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ 授權存好了（refresh_token 已寫入 config.json）")

if __name__ == "__main__":
    if sys.argv[1:] == ["auth"]: auth_flow()
    elif sys.argv[1:] == ["test"]:
        F = _cfg()["drive_folders"]; print("token OK" if token() else "no token"); print("root 子資料夾 test:", ensure_folder("_連線測試", F["root"]))
