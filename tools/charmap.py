# -*- coding: utf-8 -*-
r"""한글 음절 → 게임 코드 표 → work/charmap.tsv (음절 · 코드 hex · 글꼴 칸)
  1바이트: 반각 코드 0xA6‥0xAF·0xB1‥0xDD (55칸) — 게임은 이 코드를 표(/GAME.PRG 0x3A956, RAM 0x0605A956)로
           SJIS 히라가나(を ぁ … ん)로 바꿔 그 칸을 그린다 → 그 히라가나 칸에 한글을 그리면 1바이트 한글.
           (0xA1‥0xA5 = 。「」、・ · 0xB0 = ー 는 부호로 남긴다.) 대본에서 가장 잦은 음절 55개.
  2바이트: 나머지 음절 → JIS 제1수준 한자 칸 0x889F‥ (뒤 바이트 0x40 '@'·0x5C '\'·0x7F 는 제어·끝 표지와 겹쳐 피한다)
  ★「가나·한자 칸 전부 덮어쓴다」 — 번역하면 일본 글자는 안 쓴다.
  표는 한 번 만들면 고정(번역이 늘면 새 음절만 뒤에 붙인다 — 이미 준 코드는 안 바꾼다).
  python tools/charmap.py
"""
import collections, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ko

PATH = os.path.join(ROOT, 'work', 'charmap.tsv')
ONE = list(range(0xA1, 0xDE))                  # 반각 0xA1‥0xDD 61칸 전부
# 원래 부호(。「」、・ー)를 가리키던 6칸은 변환표(kenc.KANA_TABLE)를 고쳐 제2수준 한자 칸으로 돌린다
#   → 2바이트 「」・ー 는 원래 칸 그대로 쓸 수 있다
ONE_REMAP = {0xA1: 0xE041, 0xA2: 0xE042, 0xA3: 0xE043, 0xA4: 0xE044, 0xA5: 0xE045, 0xB0: 0xE046}
EXTRA = 'ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㅏㅓㅗㅜㅡㅣ'        # 번역에 나오는 자모(«ㄱ» 등)
ONE_EXTRA = '　‥！？（）'      # 음절 말고도 1바이트 후보(공백이 가장 잦다 — 빈 칸 글리프, 폭은 전각과 같다). 2바이트 자리엔 원래 SJIS 를 쓴다


FORCE_ONE = '카'          # 주인공 기본 이름표(GAME.PRG 0x16308·0x1E238 «ｶｼﾑ» 3바이트 칸) — «카심» = 1+2바이트여야 들어간다


def kenc_wide(ch):
    return {' ': '　', '!': '！', '?': '？', '(': '（', ')': '）'}.get(ch, ch)


def two_byte_codes():
    lead = 0x88
    while lead <= 0x9F:
        for tr in range(0x40, 0xFD):
            c = lead << 8 | tr
            if c < 0x889F or tr in (0x40, 0x5C, 0x7F) or c > 0x9872:
                continue
            yield c
        lead += 1
    for lead in range(0xE0, 0xEB):                     # 모자라면 제2수준 뒤쪽
        for tr in range(0x41, 0xFD):
            if tr not in (0x5C, 0x7F):
                yield lead << 8 | tr


def load():
    m = {}
    if os.path.exists(PATH):
        for l in open(PATH, encoding='utf-8'):
            if l.startswith('#'):
                continue
            ch, code = l.rstrip('\n').split('\t')[:2]
            m[ch] = int(code, 16)
    return m


def need():
    """번역에 쓰인 음절(자모 포함) — 대본 빈도 순"""
    c = collections.Counter()
    for n, rs in ko.all_rows().items():
        for r in rs:
            for ch in ko.body(r['ko']):
                ch = kenc_wide(ch)
                if '가' <= ch <= '힣' or ch in EXTRA or ch in ONE_EXTRA:
                    c[ch] += 3 if n == 'script.tsv' else 1   # 대본(압축 자리)이 1바이트의 덕을 가장 크게 본다
    return c


def build():
    m = load()
    c = need()
    used = set(m.values())
    if not m:                                          # 처음: 1바이트 55칸
        top = [ch for ch in FORCE_ONE] + [ch for ch, _ in c.most_common() if ch not in FORCE_ONE]
        for ch in top[:len(ONE)]:
            m[ch] = ONE[len(m)]
        used = set(m.values())
    free = (x for x in two_byte_codes() if x not in used)
    for ch, _ in c.most_common():
        if ch not in m and ch not in ONE_EXTRA:
            m[ch] = next(free)
    with open(PATH, 'w', encoding='utf-8') as f:
        f.write('#음절\t코드\n')
        for ch, code in sorted(m.items(), key=lambda kv: (kv[1] > 0xFF, kv[1])):
            f.write('%s\t%X\n' % (ch, code))
    return m


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    m = build()
    print('음절', len(m), '1바이트', sum(1 for v in m.values() if v < 0x100), '마지막 코드 %X' % max(m.values()))
