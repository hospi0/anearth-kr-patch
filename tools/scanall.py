# -*- coding: utf-8 -*-
r"""GAME.PRG 전체를 1바이트 간격으로 LZSS 블록 머리 검색(4바이트 간격 scanblocks 가 정렬 안 된 블록을 놓쳤다)
  numpy 로 머리 후보를 거른 뒤 풀어서 «소비 = 압축 크기» 확인. → work/blocks_game_all.txt
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss


def main(path, outp):
    g = open(path, 'rb').read()
    a = np.frombuffer(g, np.uint8).astype(np.uint32)
    n = len(g) - 8
    cs = a[0:n] | (a[1:n + 1] << 8) | (a[2:n + 2] << 16) | (a[3:n + 3] << 24)
    ds = a[4:n + 4] | (a[5:n + 5] << 8) | (a[6:n + 6] << 16) | (a[7:n + 7] << 24)
    ok = (cs >= 16) & (cs <= 0x40000) & (ds > cs) & (ds <= cs * 9) & (ds <= 0x80000)
    idx = np.nonzero(ok)[0]
    print('candidates', len(idx))
    res = []
    last_end = 0
    for i in idx:
        i = int(i)
        if i < last_end:
            continue
        c, d = int(cs[i]), int(ds[i])
        if i + 8 + c > len(g):
            continue
        out, end = lzss.decode(g, i + 8, d)
        if len(out) == d and end - (i + 8) == c:
            res.append((i, c, d)); last_end = i + 8 + c
    with open(outp, 'w') as f:
        for i, c, d in res:
            f.write('%08x %6d %6d 0\n' % (i, c, d))
    print('blocks', len(res))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
