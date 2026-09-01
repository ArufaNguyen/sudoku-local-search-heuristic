"""
Smoke test REST API v1 — Program A
Chay sau khi server da khoi dong tai 127.0.0.1:8000.
"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000/api/v1"

def request(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

passed = 0
failed = 0

def check(label, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  PASS  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}  <- {detail}")
        failed += 1

print()
print("=" * 55)
print("  Smoke Test: REST API v1")
print("=" * 55)

# T1: GET /health
status, body = request("GET", "/health")
check("T01 GET /health -> 200", status == 200)
check("T02 health.success == True", body.get("success") is True)
check("T03 health.service == sudoku-game", body.get("service") == "sudoku-game")

# T2: GET /game/state
status, body = request("GET", "/game/state")
check("T04 GET /game/state -> 200", status == 200)
check("T05 state.success == True", body.get("success") is True)
check("T06 state has board (9 rows)", len(body.get("board", [])) == 9)
check("T07 state has fixed mask", len(body.get("fixed", [])) == 9)
check("T08 state.status in PLAYING/CONFLICT/SOLVED",
      body.get("status") in ("PLAYING", "CONFLICT", "SOLVED"))
check("T09 state has conflicts list", isinstance(body.get("conflicts"), list))
check("T10 state has empty_cells", isinstance(body.get("empty_cells"), int))

# T3: GET /game/status
status, body = request("GET", "/game/status")
check("T11 GET /game/status -> 200", status == 200)
check("T12 status.conflict_count >= 0", body.get("conflict_count", -1) >= 0)

# T4: POST /game/move (editable cell, valid move)
status, body = request("POST", "/game/move", {"x": 0, "y": 2, "num": 4})
check("T13 POST /game/move valid -> 200", status == 200)
check("T14 move.success == True", body.get("success") is True)
check("T15 move returns status", body.get("status") in ("PLAYING", "CONFLICT", "SOLVED"))
check("T16 move returns conflicts list", isinstance(body.get("conflicts"), list))

# T5: POST /game/move -> FIXED_CELL (x=0,y=0 is fixed clue=5)
status, body = request("POST", "/game/move", {"x": 0, "y": 0, "num": 9})
check("T17 POST /game/move fixed cell -> 400", status == 400)
check("T18 error code == FIXED_CELL", body.get("error") == "FIXED_CELL")

# T6: POST /game/move -> INVALID_COORDINATE
status, body = request("POST", "/game/move", {"x": 9, "y": 0, "num": 1})
check("T19 POST /game/move x=9 -> 400", status == 400)
check("T20 error code == INVALID_COORDINATE", body.get("error") == "INVALID_COORDINATE")

# T7: POST /game/move -> INVALID_VALUE
status, body = request("POST", "/game/move", {"x": 0, "y": 2, "num": 10})
check("T21 POST /game/move num=10 -> 400", status == 400)
check("T22 error code == INVALID_VALUE", body.get("error") == "INVALID_VALUE")

# T8: POST /game/move conflict move (same num in row)
status, body = request("POST", "/game/move", {"x": 0, "y": 2, "num": 5})
check("T23 POST /game/move conflict -> 200 (accepted)", status == 200)
check("T24 conflict move status == CONFLICT", body.get("status") == "CONFLICT")
check("T25 conflicts list not empty", len(body.get("conflicts", [])) > 0)

# T9: POST /game/clear
status, body = request("POST", "/game/clear", {"x": 0, "y": 2})
check("T26 POST /game/clear editable -> 200", status == 200)
check("T27 clear.success == True", body.get("success") is True)

# T10: POST /game/clear fixed cell
status, body = request("POST", "/game/clear", {"x": 0, "y": 0})
check("T28 POST /game/clear fixed -> 400", status == 400)
check("T29 error code == FIXED_CELL", body.get("error") == "FIXED_CELL")

# T11: POST /game/reset
status, body = request("POST", "/game/reset", {})
check("T30 POST /game/reset -> 200", status == 200)
check("T31 reset returns full state", "board" in body and "fixed" in body)
check("T32 reset.status == PLAYING", body.get("status") == "PLAYING")

# T12: PUT /game/state (replace editable snapshot)
state_body = request("GET", "/game/state")[1]
board = state_body["board"]
board[0][2] = 4  # editable cell
status, body = request("PUT", "/game/state", {"board": board})
check("T33 PUT /game/state valid -> 200", status == 200)
check("T34 replace returns state with board", "board" in body)

# T13: PUT /game/state replace fixed cell -> 400
bad_board = state_body["board"]
bad_board[0][0] = 9  # fixed cell (was 5)
status, body = request("PUT", "/game/state", {"board": bad_board})
check("T35 PUT /game/state fixed change -> 400", status == 400)
check("T36 error code == FIXED_CELL", body.get("error") == "FIXED_CELL")

# T14: Invalid JSON body
import urllib.request as ur
req = ur.Request(BASE + "/game/move",
                 data=b"NOT_JSON",
                 method="POST",
                 headers={"Content-Type": "application/json"})
try:
    with ur.urlopen(req) as r: st, b = r.status, json.loads(r.read())
except urllib.error.HTTPError as e: st, b = e.code, json.loads(e.read())
check("T37 POST /game/move bad JSON -> 400", st == 400)
check("T38 error code == INVALID_JSON", b.get("error") == "INVALID_JSON")

# T15: 404 unknown route
status, body = request("GET", "/unknown/route")
check("T39 GET unknown API path -> 404", status == 404)
check("T40 error code == NOT_FOUND", body.get("error") == "NOT_FOUND")

# T16: POST /game/load
from copy import deepcopy
new_board = [[5,3,0,0,7,0,0,0,0],[6,0,0,1,9,5,0,0,0],[0,9,8,0,0,0,0,6,0],
             [8,0,0,0,6,0,0,0,3],[4,0,0,8,0,3,0,0,1],[7,0,0,0,2,0,0,0,6],
             [0,6,0,0,0,0,2,8,0],[0,0,0,4,1,9,0,0,5],[0,0,0,0,8,0,0,7,9]]
status, body = request("POST", "/game/load",
                       {"test_id": "easy_01", "difficulty": "easy", "board": new_board})
check("T41 POST /game/load -> 200", status == 200)
check("T42 load test_id == easy_01", body.get("test_id") == "easy_01")
check("T43 load difficulty == easy", body.get("difficulty") == "easy")

print()
print("=" * 55)
print(f"  Result: {passed} PASSED  |  {failed} FAILED")
print("=" * 55)
if failed:
    raise SystemExit(1)
