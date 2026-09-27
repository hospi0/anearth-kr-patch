# -*- coding: utf-8 -*-
r"""아이템 이름 폭을 원문 폭(공백 채움)으로 세자 넘친 책·신화 문구 9줄 줄이기(2026-09-27)
  → work/text/script_fix_padwidth.tsv (setko 로 반영)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ko

IDS = {'159148:10:0', '2833dc:10:0', '2833dc:11:0', '2833dc:13:0', '321370:40:0', '321370:41:0', '321370:43:0',
       '3b4984:30:1', 'b5a438:103:0'}
REPL = [('의 신으로 삼았다', '의 신으로 삼다'), ('의 ‥으로 삼았다', '의 ‥으로 삼다'),
        ('바람의영검 {03:0060}', '바람의영검{03:0060}'), ('물의 영검 {03:005f}', '물의 영검{03:005f}'),
        ('에 관련된 것이', '에 관한 것이'), ('이테르의 마법검 {01:075d}', '이테르 마법검 {01:075d}')]

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    out = []
    for r in ko.rows('script.tsv'):
        if r['ko'] and ('{01:07' in r['ko'] or '{03:00' in r['ko']):
            t = r['ko']
            for a, b in REPL:
                t = t.replace(a, b)
            if t != r['ko'] or r['id'] in IDS:
                out.append((r['id'], t))
    with open(os.path.join(ROOT, 'work', 'text', 'script_fix_padwidth.tsv'), 'w', encoding='utf-8') as f:
        f.write('#번호\tKO — 이름 원문 폭 기준으로 넘친 줄 줄임(tools/fix_padwidth.py)\n')
        for i, t in out:
            f.write('%s\t%s\n' % (i, t))
    print(len(out))
