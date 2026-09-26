# -*- coding: utf-8 -*-
r"""창에 안 들어가는 번역의 줄인 판을 script.tsv 에 반영
  work/fail_boxes_v1.tsv(번호 순 목록: 폭·줄·번호들·JP·KO원래) + work/text/script_fit.tsv(번호 · 줄인 번역)
  → script.tsv 의 해당 번호들 KO 를 바꾼다(현재 KO 가 «KO원래» 와 같을 때만 — 그 사이 누가 고쳤으면 건너뛰고 알림)
  python tools/applyfit.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    fail = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'fail_boxes_v1.tsv'), encoding='utf-8') if not l.startswith('#')]
    fit = {}
    for l in open(os.path.join(ROOT, 'work', 'text', 'script_fit.tsv'), encoding='utf-8'):
        if l.startswith('#') or not l.strip():
            continue
        n, t = l.rstrip('\n').split('\t')
        fit[int(n)] = t
    want = {}
    for i, c in enumerate(fail, 1):
        if i in fit:
            for rid in c[2].split(','):
                want[rid] = (c[4], fit[i])
    p = os.path.join(ROOT, 'work', 'text', 'script.tsv')
    lines = open(p, encoding='utf-8').read().split('\n')
    done = skip = 0
    for j, l in enumerate(lines):
        c = l.split('\t')
        if len(c) >= 3 and c[0] in want:
            old, new = want[c[0]]
            if c[2] == old:
                c[2] = new; lines[j] = '\t'.join(c); done += 1
            elif c[2] != new:
                skip += 1; print('건너뜀(이미 바뀜)', c[0])
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    print('반영', done, '건너뜀', skip)


if __name__ == '__main__':
    main()
