# -*- coding: utf-8 -*-
r"""낱말 끼움 뒤 조사 고르기 — 빌드 때 번역문의 «을(를)» 등을 실제 조사로 (2026-09-27 사용자 «을(를) 손해가 너무 커»)
  `{01:07XX}` = 아이템 이름 목록(GAME 0x2BD28 부터 NUL 로 이어진 문자열)의 XX 번째를 찍는다(`{03:00XX}` = 같은 번호 아이콘).
    확인: 霊剣 {01:075f}=仙剣シャクハール · 巻物 {01:07a0}=ライトニング · «高いお薬» {01:0724}=ハイポーション
  번호는 대본에 박힌 상수라 번역된 이름(game_plain.tsv)의 끝 받침으로 조사를 미리 정한다. 주인공 이름 {name:} 은 실행 때 정해져 그대로 둔다.
  python tools/josa.py → 바뀌는 예 출력
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ko

LIST = 0x2BD28
_names = None


def names(g=None):
    """번호 → 한국어 이름(없으면 None)"""
    global _names
    if _names is None:
        g = g or open(os.path.join(ROOT, 'work', 'GAME.PRG'), 'rb').read()
        P = {int(r['id'][1:], 16): r['ko'] for r in ko.rows('game_plain.tsv') if r['id'][0] == 'G' and r['ko']}
        _names = []; p = LIST
        while True:
            e = g.index(b'\0', p)
            if e == p:
                break
            _names.append(P.get(p)); p = e + 1
    return _names


def jong(s):
    """끝 글자 받침: None(한글 아님) / 0(없음) / 8(ㄹ) / 그 밖"""
    s = re.sub(r'[\s　‥…！？!?」』）)]+$', '', s)
    if not s or not '가' <= s[-1] <= '힣':
        return None
    return (ord(s[-1]) - 0xAC00) % 28


# (찾을 꼴, 받침 있을 때, 받침 없을 때) — 긴 꼴 먼저
FORMS = [('을(를)', '을', '를'), ('를(을)', '을', '를'), ('이(가)', '이', '가'), ('가(이)', '이', '가'),
         ('은(는)', '은', '는'), ('는(은)', '은', '는'), ('과(와)', '과', '와'), ('와(과)', '과', '와'),
         ('(으)로', '으로', '로'), ('으로', '으로', '로'), ('(이)라', '이라', '라'), ('이라', '이라', '라'),
         ('(이)나', '이나', '나'), ('(이)야', '이야', '야'),
         ('을', '을', '를'), ('를', '을', '를'), ('은', '은', '는'), ('는', '은', '는'), ('이', '이', '가'), ('가', '이', '가'),
         ('과', '과', '와'), ('와', '과', '와'), ('로', '으로', '로'), ('라', '이라', '라')]
BARE_NEXT = r'(?=$|[\s　\\{！？‥、,.!?]|도|는|고|면|서)'     # 맨 조사(을·를…)는 뒤가 공백·부호·줄바꿈일 때만(«가유명» 은 띄어쓰기 없는 번역 → 공백 기준 안 됨)
PAT = re.compile(r'(\{01:07([0-9a-f]{2})\}(?:\{(?:03|c):[0-9a-f]+\})*)')


def resolve(text, g=None):
    N = names(g)
    out = []; i = 0
    for m in PAT.finditer(text):
        out.append(text[i:m.end()]); i = m.end()
        x = int(m.group(2), 16)
        nm = N[x] if x < len(N) else None
        j = jong(nm) if nm else None
        if j is None:
            continue
        rest = text[i:]
        for f, a, b in FORMS:
            if not rest.startswith(f):
                continue
            if '(' not in f and len(f) == 1 and not re.match(re.escape(f) + BARE_NEXT, rest) and f not in '을를':
                continue
            if f in ('으로', '로'):
                pick = '로' if j in (0, 8) else '으로'
            elif f in ('(으)로',):
                pick = '로' if j in (0, 8) else '으로'
            else:
                pick = a if j else b
            out.append(pick); i += len(f)
            break
    out.append(text[i:])
    return ''.join(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    n = 0
    for r in ko.rows('script.tsv'):
        if r['ko'] and '{01:07' in r['ko']:
            t = resolve(r['ko'])
            if t != r['ko']:
                n += 1
                if n <= 40:
                    print(r['id'], '|', r['ko'][:60], '→', t[:60])
    print('바뀌는 줄', n)
