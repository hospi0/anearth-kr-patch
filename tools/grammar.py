# -*- coding: utf-8 -*-
r"""대본 명령(`%` + 연산 바이트) 인수 길이 추정 — 통계
  각 연산마다 인수 길이 후보 L(0‥12)을 대 보고, «인수 뒤 바이트»가 다음 명령(0x25)·끝(0x00/0x40)·본문 글자로
  이어지는 비율을 잰다. python tools/grammar.py
"""
import os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, extract as E


def script_msgs():
    g = open(E.GAME, 'rb').read()
    for l in open(os.path.join(ROOT, 'work', 'blocks_game.txt')):
        off, cs, ds, _ = l.split(); off = int(off, 16); ds = int(ds)
        out, _ = lzss.decode(g, off + 8, ds)
        if E.is_script(out):
            for k, a, b in E.messages(out):
                yield off, k, out[a:b]


def good_after(m, q):
    if q >= len(m):
        return True
    x = m[q]
    if x in (0x25, 0x00, 0x40, 0x5c) or 0xa1 <= x <= 0xdf:
        return True
    if (0x81 <= x <= 0x9f or 0xe0 <= x <= 0xef) and q + 1 < len(m) and (0x40 <= m[q + 1] <= 0xfc):
        return True
    return False


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    occ = collections.defaultdict(list)
    for off, k, m in script_msgs():
        for p in range(len(m) - 1):
            if m[p] == 0x25:
                occ[m[p + 1]].append((m, p))
    for op in sorted(occ):
        L = occ[op]
        sc = []
        for n in range(0, 13):
            ok = sum(1 for m, p in L if good_after(m, p + 2 + n))
            sc.append(ok / len(L))
        best = max(range(13), key=lambda n: (round(sc[n], 3), -n))
        ex = L[0][0][L[0][1]:L[0][1] + 14].hex(' ')
        print('op %02x n=%5d best L=%2d (%.3f)  L0..6=%s  ex %s' % (op, len(L), best, sc[best],
              ' '.join('%.2f' % v for v in sc[:7]), ex))


if __name__ == '__main__':
    main()
