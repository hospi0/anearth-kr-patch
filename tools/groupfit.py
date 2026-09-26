# -*- coding: utf-8 -*-
r"""묶음 자리 검사 — 대본 블록만 움직이고 그 밖 블록은 제자리(build.build_script 와 같은 규칙)
  넘치는 구간(고정 블록 앞 또는 묶음 끝)을 전부 보고한다.
  python tools/groupfit.py
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, lzss_enc, scriptfit, groups


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    tr = scriptfit.by_block()
    bad = []
    for grp, start, end in groups.groups(g):
        if not any(b[0] in tr for b in grp):
            continue
        pos = start; seg = []
        for off, cs, ds, q, d in grp:
            if off not in tr:
                if pos > off:
                    bad.append((pos - off, seg, hex(off)))
                pos = (off + 8 + cs + 3) & ~3; seg = []
                continue
            out, _ = lzss.decode(g, off + 8, ds)
            n = len(lzss_enc.encode_cached(scriptfit.rebuild(out, tr[off])))
            seg.append(hex(off))
            pos = (pos + 8 + n + 3) & ~3
        if pos > end:
            bad.append((pos - end, seg, 'end'))
    for b in bad:
        print('넘침 %d  블록 %s  (앞: %s)' % b)
    print('넘치는 구간', len(bad))


if __name__ == '__main__':
    main()
