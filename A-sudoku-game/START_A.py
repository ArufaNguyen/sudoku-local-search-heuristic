"""
START_A.py -- Khoi dong Program A (Sudoku Game & REST API)
==========================================================
Chay tu thu muc goc du an HOAC tu thu muc A-sudoku-game/:

    python A-sudoku-game/START_A.py
    python START_A.py          (neu dang o trong A-sudoku-game/)

Chuc nang:
  1. Kiem tra moi truong (Python >= 3.9, cac file can thiet).
  2. Khoi dong server tai http://127.0.0.1:8000.
  3. Cho server san sang (toi da 8 giay).
  4. Mo trinh duyet mac dinh.
  5. Giu tien trinh -- Ctrl+C de tat.

Moi truong: Python 3.9+ -- chi dung standard library.
Tac gia: Thanh vien A -- Truong Le Quoc Viet
"""

import sys
import time
import threading
import subprocess
import webbrowser
import urllib.request
from pathlib import Path

# -- Hang so --
# File nay nam trong A-sudoku-game/, nen ROOT = thu muc chua file nay
ROOT     = Path(__file__).resolve().parent   # = A-sudoku-game/
APP_DIR  = ROOT                              # app.py nam ngay tai day
APP_FILE = ROOT / "app.py"
HOST, PORT = "127.0.0.1", 8000
URL  = f"http://{HOST}:{PORT}"
API  = f"{URL}/api/v1"

# -- ANSI colors --
def _c(code):
    return f"\033[{code}m" if hasattr(sys.stdout,"isatty") and sys.stdout.isatty() else ""

R=_c(0); B=_c(1); DIM=_c(2)
GRN=_c(92); CYN=_c(96); YLW=_c(93); RED=_c(91); MAG=_c(95)

def banner():
    w = 56
    print()
    print(f"{B}{CYN}{'='*w}{R}")
    print(f"{B}{CYN}  Program A  --  Sudoku Game / REST API{R}")
    print(f"{B}{CYN}{'='*w}{R}")
    print(f"  {DIM}BTL Tri Tue Nhan Tao 2026  |  Thanh vien A{R}")
    print()

def ok(m):   print(f"  {GRN}[OK]{R}  {m}")
def info(m): print(f"  {CYN}[..]{R}  {m}")
def warn(m): print(f"  {YLW}[!!]{R}  {m}")
def fail(m): print(f"  {RED}[XX]{R}  {m}")

# -- Kiem tra moi truong --
def check():
    good = True
    v = sys.version_info
    if v >= (3, 9):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor} -- can >= 3.9"); good = False

    if APP_FILE.is_file(): ok("app.py tim thay")
    else:                  fail(f"Khong thay: {APP_FILE}"); good = False

    static = APP_DIR / "static"
    if static.is_dir():
        files = ", ".join(f.name for f in sorted(static.iterdir()) if f.is_file())
        ok(f"static/ [{files}]")
    else:
        warn("Thu muc static/ chua co -- giao dien se khong hien thi")

    for doc in ["GAME_SPECIFICATION.md", "API_SPECIFICATION.md", "TECHNICAL_REPORT.md"]:
        if (APP_DIR / doc).is_file():
            ok(doc)
        else:
            warn(f"Thieu tai lieu: {doc}")
    return good

# -- Doi server --
def wait_ready(timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{API}/health", timeout=0.5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False

# -- Chay server --
_proc = None

def run_server():
    global _proc
    _proc = subprocess.Popen(
        [sys.executable, str(APP_FILE)],
        cwd=str(APP_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _proc.wait()

# -- Main --
def main():
    banner()

    print(f"{B}Kiem tra moi truong:{R}")
    if not check():
        fail("Dung lai do thieu file can thiet.")
        sys.exit(1)

    print()
    print(f"{B}Khoi dong server:{R}")
    info(f"Dang khoi dong {URL} ...")

    t = threading.Thread(target=run_server, daemon=True, name="ServerA")
    t.start()

    if wait_ready(timeout=8.0):
        ok(f"Server san sang tai {GRN}{URL}{R}")
    else:
        warn("Server mat > 8 giay -- co the port 8000 da bi chiem.")
        warn("Kiem tra: netstat -ano | findstr :8000")

    print()
    info("Mo trinh duyet ...")
    threading.Timer(0.4, webbrowser.open, args=(URL,)).start()

    print()
    print(f"{B}{'-'*56}{R}")
    print(f"  {GRN}Program A dang chay.{R}  Nhan {B}Ctrl+C{R} de dung.")
    print(f"  URL : {GRN}{URL}{R}")
    print(f"  API : {CYN}{API}{R}")
    print(f"{B}{'-'*56}{R}")
    print()

    try:
        while t.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
        info("Dang tat server ...")
        if _proc and _proc.poll() is None:
            _proc.terminate()
            try: _proc.wait(timeout=3)
            except Exception: pass

    print()
    ok("Program A da dung. Tam biet!")
    print()

if __name__ == "__main__":
    main()
