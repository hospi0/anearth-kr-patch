# -*- coding: utf-8 -*-
r"""묶음 단위 자리 검사 — 번역 넣은 대본 블록을 최적 압축(캐시)해 묶음 자리에 다 들어가나"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lzss, lzss_enc, scriptfit, groups


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    tr = scriptfit.by_block()
    bad = 0; tot = 0; single_over = 0
    for grp, start, end in groups.groups(g):
        if not any(b[0] in tr for b in grp):
            continue
        need = 0
        for off, cs, ds, q, d in grp:
            if off in tr:
                out, _ = lzss.decode(g, off + 8, ds)
                n = len(lzss_enc.encode_cached(scriptfit.rebuild(out, tr[off])))
            else:
                n = cs
            need += (8 + n + 3) & ~3
        tot += 1
        if need > end - start:
            bad += 1
            print('묶음 %07x 블록 %d 필요 %d 자리 %d 넘침 %d' % (start, len(grp), need, end - start, need - (end - start)))
    print('대본 묶음', tot, '넘침', bad)


if __name__ == '__main__':
    main()
