# -*- coding: utf-8 -*-
r"""줄였던 번역(work/fail_boxes_v1.tsv 의 «KO 원래») 중 지금 규칙(부호 뒤 공백 삭제 포함)으로 창에 들어가는 것 → 원래 번역으로 되돌림
  python tools/restorefit.py [--write]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import boxes, scriptfit, ko


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    g = open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
    tr = scriptfit.by_block()
    keys = boxes.run_keys(g, scriptfit.blocks(), tr)
    B = boxes.load()
    cur = {r['id']: r for r in ko.rows('script.tsv')}
    back = {}; keep = 0
    for l in open(os.path.join(ROOT, 'work', 'fail_boxes_v1.tsv'), encoding='utf-8'):
        if l.startswith('#'):
            continue
        w, h, ids, jp, old = l.rstrip('\n').split('\t')[:5]
        ids = ids.split(',')
        ok = all(boxes.layout(old, jp, *B.get(keys.get(i), (16, 4)))[1] != 'fail' for i in ids)
        if ok:
            for i in ids:
                if cur[i]['ko'] != old:
                    back[i] = old
        else:
            keep += 1
    print('되돌림', len(back), '곳 / 여전히 줄여야 하는 문장', keep)
    if '--write' in sys.argv:
        p = os.path.join(ROOT, 'work', 'text', 'script_restore.tsv')
        with open(p, 'w', encoding='utf-8') as f:
            f.write('#번호\tKO(원래 번역 되돌림)\n')
            for i, t in back.items():
                f.write('%s\t%s\n' % (i, t))
        import setko
        setko.main(p)


if __name__ == '__main__':
    main()
