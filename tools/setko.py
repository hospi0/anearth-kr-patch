# -*- coding: utf-8 -*-
r"""번호 지정 번역 덮어쓰기 — TSV(번호 · KO) 를 반영
  번호가 G…/B…/S… 면 game_plain.tsv/battle.tsv(4열), 그 밖은 script.tsv(3열)
  python tools/setko.py work/text/script_fix_ids.tsv
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def target(rid):
    if rid[0] == 'G':
        return 'game_plain.tsv', 3
    if rid[0] in 'BS':
        return 'battle.tsv', 3
    return 'script.tsv', 2


def main(src):
    sys.stdout.reconfigure(encoding='utf-8')
    want = {}
    for l in open(src, encoding='utf-8'):
        if l.startswith('#') or not l.strip():
            continue
        rid, t = l.rstrip('\n').split('\t')
        want.setdefault(target(rid), {})[rid] = t
    done = set()
    for (name, col), ws in want.items():
        p = os.path.join(ROOT, 'work', 'text', name)
        lines = open(p, encoding='utf-8').read().split('\n')
        for j, l in enumerate(lines):
            c = l.split('\t')
            if len(c) > col and c[0] in ws:
                c[col] = ws[c[0]]; lines[j] = '\t'.join(c); done.add(c[0])
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    miss = {r for ws in want.values() for r in ws} - done
    print('반영', len(done), '없는 번호', sorted(miss))


if __name__ == '__main__':
    main(sys.argv[1])
