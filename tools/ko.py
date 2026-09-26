# -*- coding: utf-8 -*-
r"""번역 읽기 공용 — work/text/{script,game_plain,battle}.tsv 의 KO 열
  script.tsv: 번호 · JP · KO        game_plain/battle.tsv: 위치 · 예산(B) · JP · KO
"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TEXT = os.path.join(ROOT, 'work', 'text')
TOKEN = re.compile(r'\{[^}]*\}|\\n')


def rows(name):
    out = []
    for l in open(os.path.join(TEXT, name), encoding='utf-8'):
        if l.startswith('#'):
            continue
        c = l.rstrip('\n').split('\t')
        if name == 'script.tsv':
            out.append(dict(id=c[0], jp=c[1], ko=c[2] if len(c) > 2 else ''))
        else:
            out.append(dict(id=c[0], budget=int(c[1]), jp=c[2], ko=c[3] if len(c) > 3 else ''))
    return out


def all_rows():
    return {n: rows(n) for n in ('script.tsv', 'game_plain.tsv', 'battle.tsv')}


def body(t):
    return TOKEN.sub('', t)
