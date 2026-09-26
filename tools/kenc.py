# -*- coding: utf-8 -*-
r"""번역 표기 → 게임 바이트
  표기: `{c:XX}`(%04 XX) · `{name:XXXX}`(%00 XX XX) · `{op:hex}`(% op + 인수, extract.INLINE) · `\n`(0x5C) · 글자
  한글 = work/charmap.tsv (1바이트 0xA6‥ / 2바이트 한자 칸) · 나머지는 cp932(반각 영숫자·부호·공백 → 전각)
  sjis_only=True: 1바이트 코드를 못 쓰는 곳(BATTLE 보스 대사) — 1바이트 음절은 그 코드가 가리키는 히라가나 SJIS 로.
  ★규칙(쓰는 순간 강제): 문장부호 뒤 공백 삭제 · 반각 공백 → 전각(0x8140) · 글꼴에 없는 글자 = 오류
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import charmap

KANA_TABLE = 0x3A956          # GAME.PRG — 반각 0xA1‥0xDD → SJIS (2B BE) 61개
_map = None
_kana = None


def cmap():
    global _map
    if _map is None:
        _map = charmap.load()
    return _map


def kana_table(game):
    """반각 코드 → SJIS 코드(= 글꼴 칸). 원래 표 + charmap.ONE_REMAP(빌더가 표에 쓴다)"""
    t = {0xA1 + i: struct.unpack_from('>H', game, KANA_TABLE + 2 * i)[0] for i in range(0xDE - 0xA1)}
    t.update(charmap.ONE_REMAP)
    return t


PUNCT_SPACE = re.compile(r'([,.!?:;，．！？：；]) (?=[^ 　])')   # 반각 공백만 — 전각 공백은 선택지·목록 칸 맞춤에 쓰인다
WIDE = {' ': '　', '(': '（', ')': '）', ',': '，', '.': '．', '!': '！', '?': '？', ':': '：', ';': '；',
        '~': '～', '-': '－', '/': '／', '%': '％', '&': '＆', '+': '＋', "'": '’', '"': '”', '*': '＊'}


def normalize(t):
    t = PUNCT_SPACE.sub(r'\1', t)
    return t


def enc(t, sjis_only=False, kt=None):
    m = cmap()
    t = normalize(t)
    out = bytearray()
    for tok in re.split(r'(\{[^}]*\}|\\n)', t):
        if not tok:
            continue
        if tok == '\\n':
            out.append(0x5C); continue
        mm = re.fullmatch(r'\{c:([0-9a-f]{2})\}', tok)
        if mm:
            out += b'%\x04' + bytes.fromhex(mm.group(1)); continue
        mm = re.fullmatch(r'\{name:([0-9a-f]{4})\}', tok)
        if mm:
            out += b'%\x00' + bytes.fromhex(mm.group(1)); continue
        mm = re.fullmatch(r'\{([0-9a-f]{2}):([0-9a-f]*)\}', tok)
        if mm:
            out += b'%' + bytes.fromhex(mm.group(1) + mm.group(2)); continue
        if tok.startswith('{'):
            raise ValueError('모르는 표기 %r' % tok)
        for ch in tok:
            ch = WIDE.get(ch, ch)
            if 'A' <= ch <= 'Z' or 'a' <= ch <= 'z' or '0' <= ch <= '9':
                ch = chr(ord(ch) + 0xFEE0)
            if ch in m:
                c = m[ch]
                if c < 0x100:
                    if sjis_only:
                        out += struct.pack('>H', kt[c])
                    else:
                        out.append(c)
                else:
                    out += struct.pack('>H', c)
            else:
                b = ch.encode('cp932')
                if len(b) != 2:
                    raise ValueError('전각 아닌 글자 %r' % ch)
                out += b
    return bytes(out)


def cells(text):
    """화면 칸 수(줄마다) — 모든 글자 1칸, 제어 0칸"""
    t = normalize(text)
    return [len(re.sub(r'\{[^}]*\}', '', ln)) for ln in t.split('\\n')]
