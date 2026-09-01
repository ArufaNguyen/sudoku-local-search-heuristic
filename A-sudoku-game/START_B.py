"""
START_B.py -- Khoi dong Program B (Auto Solver / Algorithm Visualizer)
=======================================================================
Chay tu thu muc goc du an HOAC tu thu muc A-sudoku-game/:

    python A-sudoku-game/START_B.py
    python START_B.py          (neu dang o trong A-sudoku-game/)

Luu y: Program A (port 8000) PHAI dang chay truoc.
        B se ket noi toi A ngay khi Prepare duoc bam.

Chuc nang:
  1. Kiem tra moi truong (Python >= 3.9, cac file can thiet).
  2. Khoi dong server tai http://127.0.0.1:8001.
  3. Cho server san sang (toi da 8 giay).
  4. Mo trinh duyet mac dinh.
  5. Giu tien trinh -- Ctrl+C de tat.

Moi truong: Python 3.9+ -- chi dung standard library.
Tac gia: Thanh vien B
"""

import sys
import time
import threading
import subprocess
import webbrowser
import urllib.request
from pathlib import Path

# -- Hang so --
# File nay nam trong A-sudoku-game/, nen ROOT.parent = thu muc goc du an
HERE     = Path(__file__).resolve().parent   # = A-sudoku-game/
PROJECT  = HERE.parent                       # = thu muc goc du an
APP_DIR  = PROJECT / "B-auto-solver"
APP_FILE = APP_DIR / "app.py"
HOST     = "127.0.0.1"
PORT_B   = 8001
PORT_A   = 8000
URL_B    = f"http://{HOST}:{PORT_B}"
URL_A    = f"http://{HOST}:{PORT_A}"

# -- ANSI colors --
def _c(code):
    return f"\033[{code}m" if hasattr(sys.stdout,"isatty") and sys.stdout.isatty() else ""

R=_c(0); B=_c(1); DIM=_c(2)
GRN=_c(92); CYN=_c(96); YLW=_c(93); RED=_c(91); MAG=_c(95)

def banner():
    w = 56
    print()
    print(f"{B}{MAG}{'='*w}{R}")
    print(f"{B}{MAG}  Program B  --  AI Auto Solver / Visualizer{R}")
    print(f"{B}{MAG}{'='*w}{R}")
    print(f"  {DIM}BTL Tri Tue Nhan Tao 2026  |  Thanh vien B{R}")
    print()

def ok(m):   print(f"  {GRN}[OK]{R}  {m}")
def info(m): print(f"  {CYN}[..]{R}  {m}")
def warn(m): print(f"  {YLW}[!!]{R}  {m}")
def fail(m): print(f"  {RED}[XX]{R}  {m}")

# -- Kiem tra Program A --
def check_program_a():
    try:
        with urllib.request.urlopen(f"{URL_A}/api/v1/health", timeout=1.5) as r:
            return r.status == 200
    except Exception:
        return False

# -- Kiem tra moi truong --
def check():
    good = True
    v = sys.version_info
    if v >= (3, 9):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor} -- can >= 3.9"); good = False

    if APP_DIR.is_dir():  ok("B-auto-solver/ tim thay")
    else:                 fail(f"Khong thay thu muc: {APP_DIR}"); good = False

    if APP_FILE.is_file(): ok("B-auto-solver/app.py")
    else:                  fail("Thieu B-auto-solver/app.py"); good = False

    static = APP_DIR / "static"
    if static.is_dir():
        files = ", ".join(f.name for f in sorted(static.iterdir()) if f.is_file())
        ok(f"static/ [{files}]")
    else:
        warn("Thu muc static/ chua co -- giao dien se khong hien thi")

    dataset = APP_DIR / "dataset" / "puzzles.json"
    if dataset.is_file():
        ok("dataset/puzzles.json (40 puzzles)")
    else:
        warn("Thieu dataset/puzzles.json -- B se khong doc duoc puzzle")

    for doc in ["SPECIFICATION.md", "TEST_PLAN.md", "COMPLEXITY_ANALYSIS.md", "BENCHMARK_SUMMARY.md"]:
        if (APP_DIR / doc).is_file():
            ok(doc)
        else:
            warn(f"Thieu tai lieu: {doc}")

    # Kiem tra Program A
    print()
    print(f"{B}Kiem tra Program A:{R}")
    if check_program_a():
        ok(f"Program A dang chay tai {URL_A}")
    else:
        warn(f"Program A chua phat hien tai {URL_A}")
        warn("Hay chay 'python A-sudoku-game/START_A.py' truoc,")
        warn("hoac dung 'python A-sudoku-game/START_ALL.py'")

    return good

# -- Doi server --
def wait_ready(timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{URL_B}/api/session", timeout=0.5) as r:
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
    info(f"Dang khoi dong {URL_B} ...")

    t = threading.Thread(target=run_server, daemon=True, name="ServerB")
    t.start()

    if wait_ready(timeout=8.0):
        ok(f"Server san sang tai {GRN}{URL_B}{R}")
    else:
        warn("Server mat > 8 giay -- co the port 8001 da bi chiem.")
        warn("Kiem tra: netstat -ano | findstr :8001")

    print()
    info("Mo trinh duyet ...")
    threading.Timer(0.4, webbrowser.open, args=(URL_B,)).start()

    print()
    print(f"{B}{'-'*56}{R}")
    print(f"  {GRN}Program B dang chay.{R}  Nhan {B}Ctrl+C{R} de dung.")
    print(f"  URL  : {GRN}{URL_B}{R}")
    print(f"  A URL: {CYN}{URL_A}{R}  (Program A phai chay truoc)")
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
    ok("Program B da dung. Tam biet!")
    print()

if __name__ == "__main__":
    main()
