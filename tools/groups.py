# -*- coding: utf-8 -*-
r"""블록 묶음 — 같은 포인터 표(연속 4바이트 칸, 같은 delta)에 달린 연속 블록들
  묶음 안에서는 블록을 차례로 다시 채워 넣고 표의 포인터를 고친다 → 한 블록이 넘쳐도 이웃 여유로 흡수.
  묶음 자리 = 첫 블록 시작 ‥ 마지막 블록 끝(4바이트 올림) + 바로 뒤 0 바이트(여유).
  포인터를 못 찾은 블록 = 혼자 묶음(움직이지 않는다, 자리 = 자기 끝 + 뒤 0 바이트).
  첫 블록은 절대 움직이지 않는다(그 주소를 다른 곳이 가리킬 수 있다).
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def load_ptr():
    P = {}
    for l in open(os.path.join(ROOT, 'work', 'blockptr.tsv')):
        if l.startswith('#'):
            continue
        b, q, d, s = l.split()
        d = int(d, 16)
        if d >= 0x80000000:
            d -= 1 << 32
        P[int(b, 16)] = (int(q, 16), d)
    return P


def blocks():
    return [(int(o, 16), int(c), int(d)) for o, c, d, _ in (l.split() for l in open(os.path.join(ROOT, 'work', 'blocks_game_all.txt')))]


def slot_end(g, off, cs, limit):
    """블록 끝(4바이트 올림) 뒤로 0 바이트가 이어지는 곳까지(다음 블록 시작 limit 은 넘지 않는다)"""
    e = (off + 8 + cs + 3) & ~3
    while e + 4 <= limit and g[e:e + 4] == b'\x00\x00\x00\x00':
        e += 4
    return min(e, limit)


def groups(g=None):
    """[(블록 목록[(off, cs, ds, 포인터 위치 | None, delta | None)], 자리 시작, 자리 끝)]"""
    if g is None:
        g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    P = load_ptr()
    bl = blocks()
    starts = [b[0] for b in bl] + [len(g)]
    out = []; cur = []
    for i, (off, cs, ds) in enumerate(bl):
        q, d = P.get(off, (None, None))
        if cur:
            po, pc, pds, pq, pdl = cur[-1]
            ok = (q is not None and pq is not None and q == pq + 4 and pdl == d
                  and off - ((po + 8 + pc + 3) & ~3) < 4)
            if not ok:
                out.append(cur); cur = []
        cur.append((off, cs, ds, q, d))
    if cur:
        out.append(cur)
    res = []
    for grp in out:
        last = grp[-1]
        nxt = starts[starts.index(last[0]) + 1]
        res.append((grp, grp[0][0], slot_end(g, last[0], last[1], nxt)))
    return res
