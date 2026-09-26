# -*- coding: utf-8 -*-
r"""GAME.PRG·BATTLE.PRG 안의 LZSS 블록 찾기 — 머리 [u32 LE 압축 크기][u32 LE 풀린 크기] + LZSS(tools/lzss.py, 사전 채움 창)
  조건: 풀었을 때 소비한 바이트 = 압축 크기, 풀린 길이 = 풀린 크기
  python tools/scanblocks.py <파일> [시작] [끝]  → 목록 출력(오프셋 · 압축 · 풀림 · 반각가나 비율)
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lzss


def scan(g, lo=0, hi=None, step=4):
    hi = hi or len(g) - 8
    res = []
    i = lo
    while i < hi:
        cs, ds = struct.unpack_from('<II', g, i)
        if 16 <= cs <= 0x40000 and cs < ds <= cs * 9 and ds <= 0x80000 and i + 8 + cs <= len(g):
            out, end = lzss.decode(g, i + 8, ds)
            if len(out) == ds and end - (i + 8) == cs:
                kana = sum(1 for b in out if 0xA6 <= b <= 0xDD) / ds
                res.append((i, cs, ds, kana))
                i += 8 + cs
                i = (i + step - 1) // step * step
                continue
        i += step
    return res


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(sys.argv[1], 'rb').read()
    lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    for i, cs, ds, k in scan(g, lo, hi):
        print('%08x %6d %6d %.2f' % (i, cs, ds, k))
