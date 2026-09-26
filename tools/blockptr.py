# -*- coding: utf-8 -*-
r"""LZSS 블록을 가리키는 포인터 표 찾기 → work/blockptr.tsv
  장면 덩어리(GAME.PRG 의 한 구간)는 통째로 RAM 에 올라가고, 블록은 RAM 절대 주소(u32 BE)로 가리킨다.
  예: 덩어리 0x94000‥ → RAM +0x196800, 0xAF664 표 = 블록 AF67C·AFD78·B069C·B0D3C·B0FF8·B20B8.
  ★판정(2026-09-27 다시 씀 — 첫 판은 «이웃 칸 점수» 만 봐서 서로 다른 블록에 같은 포인터를 주는 등 틀렸다):
    이웃한 두 블록 A<B 에 대해 표의 이웃 칸 (v, w) 가 w − v == B − A 이고 v 가 RAM 범위면 → 칸 q 는 A, q+4 는 B,
    delta = v − A. 한 블록에 후보가 여럿이면 앞·뒤 짝 양쪽에서 같은 (q, delta) 로 확인된 것을 고른다.
  열: 블록 · 포인터 위치 · delta · 확인 수(1 = 한쪽 짝만, 2 = 양쪽)
  python tools/blockptr.py
"""
import collections, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

RAMS = [(0x00200000, 0x00300000), (0x06000000, 0x06100000)]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    bl = [(int(o, 16), int(c), int(d)) for o, c, d, _ in (l.split() for l in open(os.path.join(ROOT, 'work', 'blocks_game_all.txt')))]
    a = np.frombuffer(g[:len(g) // 4 * 4], dtype='>u4').astype(np.int64)
    inram = np.zeros(len(a), bool)
    for lo, hi in RAMS:
        inram |= (a >= lo) & (a < hi)
    diff = np.zeros(len(a), np.int64); diff[:-1] = a[1:] - a[:-1]
    cand = collections.defaultdict(collections.Counter)      # 블록 → (q, delta) → 확인 수
    for i in range(len(bl) - 1):
        A, B = bl[i][0], bl[i + 1][0]
        D = B - A
        if D <= 0 or D > 0x40000:
            continue
        lo = max(0, (A - 0x80000) // 4); hi = min(len(a) - 1, (B + 0x80000) // 4)
        idx = np.nonzero((diff[lo:hi] == D) & inram[lo:hi] & inram[lo + 1:hi + 1])[0] + lo
        for j in idx:
            v = int(a[j]); q = int(j) * 4
            cand[A][(q, v - A)] += 1
            cand[B][(q + 4, v - A)] += 1
    res = {}
    for off, c in cand.items():
        n = max(c.values())
        tops = sorted((abs(off - q), q, d) for (q, d), v in c.items() if v == n)   # 같은 확인 수면 블록에 가장 가까운 표(표는 블록 바로 앞에 있다)
        _, q, d = tops[0]
        amb = len(tops) > 1 and tops[1][0] - tops[0][0] < 0x100 and tops[1][2] != d
        res[off] = (q, d, n, amb)
    # 한 포인터 위치를 두 블록이 가지면 둘 다 버린다
    byq = collections.Counter(v[0] for v in res.values())
    good = {o: v for o, v in res.items() if not v[3] and byq[v[0]] == 1}
    # 2단계: 확정 못 한 블록 — 앞뒤 8블록 안의 확정 delta 로 «그 RAM 주소 값이 ±0x80000 안에 딱 한 번» 이면 채택
    offs = [b[0] for b in bl]
    import re
    for i, off in enumerate(offs):
        if off in good:
            continue
        ds = {good[offs[j]][1] for j in range(max(0, i - 8), min(len(offs), i + 9)) if offs[j] in good}
        found = set()
        for d in ds:
            v = struct.pack('>I', (off + d) & 0xFFFFFFFF)
            lo = max(0, off - 0x80000)
            for m in re.finditer(re.escape(v), g[lo:off + 0x80000]):
                if (lo + m.start()) % 4 == 0:
                    found.add((lo + m.start(), d))
        if len(found) == 1:
            q, d = found.pop()
            res[off] = (q, d, 0, False)
    byq = collections.Counter(v[0] for v in res.values())
    with open(os.path.join(ROOT, 'work', 'blockptr.tsv'), 'w') as f:
        f.write('#블록\t포인터\tdelta\t확인수\n')
        bad = 0
        for off in sorted(res):
            q, d, n, amb = res[off]
            if amb or byq[q] > 1:
                bad += 1
                continue
            f.write('%x\t%x\t%x\t%d\n' % (off, q, d & 0xFFFFFFFF, n))
    print('블록', len(bl), '포인터', len(res) - bad, '모호해서 버림', bad)


if __name__ == '__main__':
    main()
