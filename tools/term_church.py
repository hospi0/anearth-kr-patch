# -*- coding: utf-8 -*-
r"""서양식 교회 용어로(2026-09-27 사용자): 僧侶 승려→사제 · 修道僧 수도승→수도사 · お坊さん 스님→신부님
  수도승(받침 ㅇ)→수도사(받침 없음) 뒤 조사도 바꾼다. → work/text/script_fix_church.tsv (setko 로 반영)
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ko

REPL = [('승려', '사제'), ('스님', '신부님')]
JOSA = {'은': '는', '이': '가', '을': '를', '과': '와', '으로': '로', '이라': '라', '이야': '야', '이여': '여'}


def fix(t):
    for a, b in REPL:
        t = t.replace(a, b)
    def sub(m):
        j = m.group(1)
        return '수도사' + JOSA.get(j, j)
    return re.sub(r'수도승(으로|이라|이야|이여|은|이|을|과)?', lambda m: '수도사' + (JOSA.get(m.group(1), m.group(1)) if m.group(1) else ''), t)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    rows = []
    for name in ('script.tsv', 'game_plain.tsv', 'battle.tsv'):
        for r in ko.rows(name):
            if r['ko'] and fix(r['ko']) != r['ko']:
                rows.append((r['id'], fix(r['ko'])))
    with open(os.path.join(ROOT, 'work', 'text', 'script_fix_church.tsv'), 'w', encoding='utf-8') as f:
        f.write('#번호\tKO — 승려→사제·수도승→수도사·스님→신부님(tools/term_church.py 생성)\n')
        for i, t in rows:
            f.write('%s\t%s\n' % (i, t))
    print(len(rows))
    for i, t in rows[:60]:
        if '수도사' in t and not t.startswith('{c:07}수도사'):
            print(i, t[:60])
