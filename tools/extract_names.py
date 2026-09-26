# -*- coding: utf-8 -*-
r"""평문 보충 추출 — «NUL 바로 뒤에서 시작해 NUL 로 끝나는» 문자열 중 기존 game_plain/battle.tsv 에 없는 것
  ★2026-09-27: 반각 히라가나 적 이름 표(BATTLE 0x24AE0‥, «ｼﾙﾊﾞｰ» 등 48개)와 제2수준 한자 기술 이름(«魔龍咆哮»)이
    extract_plain 에서 빠졌다(앞 자료와 붙어 읽히거나 글자 허용 목록 밖).
  판정: 전부 글자(반각 가나·SJIS)로 읽히고 {xx} 없음, 가나·한자 2자 이상, 같은 글자 4번 반복 없음.
  → 기존 TSV 끝에 줄을 덧붙인다(번역 칸 빈 채). 예산 = 원문 바이트.
  python tools/extract_names.py [--write]
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import extract as E
import extract_plain as P

STR = re.compile(rb'(?<=\x00)((?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\xa1-\xdf])+)(?=\x00)')
AREAS = {'GAME.PRG': [(0, 0x100000), (0x43D7E00, 0x43D8000)], 'BATTLE.PRG': [(0, 0x100000)]}


def scan(fn, tag, have, skip):
    d = open(os.path.join(ROOT, 'work', fn), 'rb').read()
    rows = []
    for a, b in AREAS[fn]:
        for m in STR.finditer(d, a, b):
            s, e = m.start(1), m.end(1)
            if s in have or any(x <= s < y for x, y in skip):
                continue
            t = E.render(d[s:e])
            if re.search(r'\{[0-9a-f]{2}\}', t) or re.search(r'(.)\1\1\1', t):
                continue
            if len(E.REAL.findall(t)) < 2:
                continue
            if len(t) < 3 and not (tag == 'B' and 0x24A00 <= s < 0x24E00):   # 2글자 = 잡음(적 이름 구역 «くま» 만 예외)
                continue
            try:
                d[s:e].decode('cp932')
            except UnicodeDecodeError:
                pass
            rows.append(('%s%07x' % (tag, s), e - s, t))
    return rows


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for fn, tsv, tag, bl in (('GAME.PRG', 'game_plain.tsv', 'G', 'blocks_game_all.txt'), ('BATTLE.PRG', 'battle.tsv', 'B', 'blocks_battle_all.txt')):
        p = os.path.join(ROOT, 'work', 'text', tsv)
        have = set()
        for l in open(p, encoding='utf-8'):
            if not l.startswith('#'):
                have.add(int(l.split('\t')[0][1:], 16))
        rows = scan(fn, tag, have, P.blocks(os.path.join(ROOT, 'work', bl)))
        print(tsv, '새 줄', len(rows))
        for r in rows:
            print('  ', *r)
        if '--write' in sys.argv and rows:
            with open(p, 'a', encoding='utf-8') as f:
                for r in rows:
                    f.write('%s\t%d\t%s\t\n' % r)


if __name__ == '__main__':
    main()
