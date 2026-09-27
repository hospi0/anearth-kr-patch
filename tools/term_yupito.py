# -*- coding: utf-8 -*-
r"""유피토촌·유피토 마을 → 유피토마을(붙여 씀) + «잘 지내‥ 야» → «잘 지내‥»(사용자 2026-09-27)
  → work/text/script_fix_yupito.tsv (setko 로 반영)
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ko


def fix(t):
    t = t.replace('유피토촌으로', '유피토마을로').replace('유피토촌', '유피토마을').replace('유피토 마을', '유피토마을')
    t = t.replace('잘 지내‥ 야', '잘 지내‥')
    return t


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    rows = []
    for name in ('script.tsv', 'game_plain.tsv', 'battle.tsv'):
        for r in ko.rows(name):
            if r['ko'] and fix(r['ko']) != r['ko']:
                rows.append((r['id'], fix(r['ko'])))
    with open(os.path.join(ROOT, 'work', 'text', 'script_fix_yupito.tsv'), 'w', encoding='utf-8') as f:
        f.write('#번호\tKO — 유피토마을 통일·«잘 지내‥» (tools/term_yupito.py 생성)\n')
        for i, t in rows:
            f.write('%s\t%s\n' % (i, t))
    print(len(rows))
