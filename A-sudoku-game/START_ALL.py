"""
START_ALL.py -- Khoi dong toan bo he thong (Program A + Program B)
===================================================================
Chay tu thu muc goc du an HOAC tu thu muc A-sudoku-game/:

    python A-sudoku-game/START_ALL.py
    python START_ALL.py          (neu dang o trong A-sudoku-game/)

Trinh tu:
  1. Kiem tra ca hai thu muc A-sudoku-game/ va B-auto-solver/.
  2. Khoi dong Program A (port 8000) -- Sudoku Game & REST API.
  3. Doi A san sang (toi da 10 giay).
  4. Khoi dong Program B (port 8001) -- AI Auto Solver.
  5. Doi B san sang (toi da 10 giay).
  6. Mo hai tab trinh duyet: A truoc, B sau.
  7. Giu ca hai tien trinh -- Ctrl+C de tat het.

Moi truong: Python 3.9+ -- chi dung standard library.
"""

import sys
import time
import threading
import subprocess
import webbrowser
import urllib.request
from pathlib import Path

# -- Hang so --
# File nay nam trong A-sudoku-game/, nen PROJECT = parent
HERE   = Path(__file__).resolve().parent   # = A-sudoku-game/
PROJECT = HERE.parent                      # = thu muc goc du an
A_DIR  = HERE                              # A-sudoku-game/ chinh la HERE
B_DIR  = PROJECT / "B-auto-solver"
A_FILE = A_DIR / "app.py"
B_FILE = B_DIR / "app.py"

URL_A = "http://127.0.0.1:8000"
URL_B = "http://127.0.0.1:8001"
API_A = f"{URL_A}/api/v1"

# -- ANSI colors --
def _c(code):
    return f"\033[{code}m" if hasattr(sys.stdout,"isatty") and sys.stdout.isatty() else ""

R=_c(0); B=_c(1); DIM=_c(2)
GRN=_c(92); CYN=_c(96); YLW=_c(93); RED=_c(91); MAG=_c(95); WHT=_c(97)

def banner():
    w = 58
    print()
    print(f"{B}{WHT}{'='*w}{R}")
    print(f"{B}{WHT}  Sudoku AI Project  --  BTL Tri Tue Nhan Tao 2026{R}")
    print(f"{B}{WHT}{'='*w}{R}")
    print(f"  {DIM}Program A  (port 8000) : Sudoku Game & REST API{R}")
    print(f"  {DIM}Program B  (port 8001) : AI Auto Solver & Visualizer{R}")
    print()

def ok(m):    print(f"  {GRN}[OK]{R}  {m}")
def info(m):  print(f"  {CYN}[..]{R}  {m}")
def warn(m):  print(f"  {YLW}[!!]{R}  {m}")
def fail(m):  print(f"  {RED}[XX]{R}  {m}")
def head(m):  print(f"\n{B}{m}{R}")

# -- Kiem tra tien quyet --
def check_prereqs():
    good = True
    v = sys.version_info
    if v >= (3, 9):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor} -- can >= 3.9"); good = False

    for label, d, f in [
        ("A-sudoku-game/", A_DIR, A_FILE),
        ("B-auto-solver/", B_DIR, B_FILE),
    ]:
        if d.is_dir() and f.is_file():
            ok(f"{label}app.py")
        else:
            fail(f"Khong tim thay {label}app.py"); good = False
    return good

# -- Doi endpoint --
def wait_url(url, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.6) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.25)
    return False

# -- Chay tien trinh --
_procs = []

def launch(app_file, cwd, name):
    p = subprocess.Popen(
        [sys.executable, str(app_file)],
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _procs.append(p)
    p.wait()

# -- Main --
def main():
    banner()

    head("Kiem tra moi truong:")
    if not check_prereqs():
        fail("Khong the khoi dong -- thieu file can thiet.")
        sys.exit(1)

    # -- Khoi dong A --
    head("Khoi dong Program A:")
    info(f"Dang khoi dong {URL_A} ...")
    ta = threading.Thread(target=launch, args=(A_FILE, A_DIR, "A"), daemon=True)
    ta.start()

    if wait_url(f"{API_A}/health", timeout=10.0):
        ok(f"Program A san sang  -->  {GRN}{URL_A}{R}")
    else:
        warn("Program A mat > 10 giay (tiep tuc nhung co the loi).")

    # -- Khoi dong B --
    head("Khoi dong Program B:")
    info(f"Dang khoi dong {URL_B} ...")
    tb = threading.Thread(target=launch, args=(B_FILE, B_DIR, "B"), daemon=True)
    tb.start()

    if wait_url(f"{URL_B}/api/session", timeout=10.0):
        ok(f"Program B san sang  -->  {GRN}{URL_B}{R}")
    else:
        warn("Program B mat > 10 giay (tiep tuc nhung co the loi).")

    # -- Mo trinh duyet --
    print()
    info("Mo trinh duyet ...")
    threading.Timer(0.4, webbrowser.open, args=(URL_A,)).start()
    threading.Timer(1.2, webbrowser.open, args=(URL_B,)).start()

    # -- Summary --
    print()
    print(f"{B}{'='*58}{R}")
    print(f"  {GRN}He thong dang chay.{R}  Nhan {B}Ctrl+C{R} de tat het.")
    print(f"  {CYN}Program A{R} : {GRN}{URL_A}{R}")
    print(f"  {MAG}Program B{R} : {GRN}{URL_B}{R}")
    print(f"{B}{'='*58}{R}")
    print()

    # -- Giu cho den Ctrl+C --
    try:
        while ta.is_alive() or tb.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
        info("Dang tat ca Program A va B ...")
        for p in _procs:
            if p.poll() is None:
                p.terminate()
        for p in _procs:
            try: p.wait(timeout=4)
            except Exception: pass

    print()
    ok("Tat ca da dung. Tam biet!")
    print()

if __name__ == "__main__":
    main()
