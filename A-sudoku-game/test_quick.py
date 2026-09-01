import sys
sys.path.insert(0, 'A-sudoku-game')
from game import SudokuGame, GameError, DEFAULT_BOARD
from copy import deepcopy

g = SudokuGame()

# T1: Fixed cell protection
try:
    g.move(0, 0, 9)
    print('FAIL T1: Fixed cell not protected')
except GameError as e:
    assert e.code == 'FIXED_CELL'
    print('PASS T1 - Fixed cell protected, code=' + e.code)

# T2: Conflict move accepted, status = CONFLICT
r = g.move(0, 2, 5)  # 5 already in row 0 col 0
assert r['status'] == 'CONFLICT'
assert len(r['conflicts']) > 0
print('PASS T2 - Conflict accepted: status=' + r['status'] + ', conflicts=' + str(len(r['conflicts'])))

# T3: replace rejects fixed cell change
g.reset()
bad = deepcopy(DEFAULT_BOARD)
bad[0][0] = 9  # (0,0) is fixed=5
try:
    g.replace(bad)
    print('FAIL T3: replace should reject fixed cell change')
except GameError as e:
    assert e.code == 'FIXED_CELL'
    print('PASS T3 - replace rejects fixed change, code=' + e.code)

# T4: replace allows conflict in editable cells
g.reset()
snap = deepcopy(DEFAULT_BOARD)
snap[0][2] = 5  # editable conflict
s = g.replace(snap)
assert s['status'] == 'CONFLICT'
print('PASS T4 - replace allows editable conflict: status=' + s['status'])

# T5: reset restores board
g.reset()
s = g.state()
assert s['status'] == 'PLAYING'
assert s['empty_cells'] == 51
print('PASS T5 - reset: status=' + s['status'] + ', empty=' + str(s['empty_cells']))

# T6: clear editable cell
g.reset()
g.move(0, 2, 4)
r = g.clear(0, 2)
assert r['status'] == 'PLAYING'
print('PASS T6 - clear editable cell ok')

# T7: clear fixed cell rejected
try:
    g.clear(0, 0)
    print('FAIL T7: clear fixed cell should be rejected')
except GameError as e:
    assert e.code == 'FIXED_CELL'
    print('PASS T7 - clear fixed rejected, code=' + e.code)

# T8: load new board
new_board = deepcopy(DEFAULT_BOARD)
res = g.load('hard_01', 'hard', new_board)
assert res['test_id'] == 'hard_01'
assert res['difficulty'] == 'hard'
print('PASS T8 - load: test_id=' + res['test_id'])

# T9: invalid coordinate
try:
    g.move(9, 0, 1)
    print('FAIL T9: should reject x=9')
except GameError as e:
    assert e.code == 'INVALID_COORDINATE'
    print('PASS T9 - invalid coord rejected, code=' + e.code)

# T10: invalid value
try:
    g.move(0, 2, 10)
    print('FAIL T10: should reject num=10')
except GameError as e:
    assert e.code == 'INVALID_VALUE'
    print('PASS T10 - invalid value rejected, code=' + e.code)

print()
print('All 10 tests PASSED!')
