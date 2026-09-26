# -*- coding: utf-8 -*-
r"""대사 문자 코드 가설: 히라가나 = 반각 가타카나 1바이트(0xA1‥0xDF, 탁음은 ﾞ/ﾟ 덧붙임), 그 밖(한자·가타카나·부호) = SJIS 2바이트
  (GAME.PRG 0xB0E00 부근을 풀었더니 «最初ﾆ見ﾂｹﾗﾚﾀ» «怪ｼｲ野郎がｲﾃ» 꼴)
"""
import unicodedata

HALF = {}
for c in range(0xA1, 0xE0):
    fw = unicodedata.normalize('NFKC', bytes([c]).decode('cp932'))
    HALF[fw] = bytes([c])
for fw in 'ガギグゲゴザジズゼゾダヂヅデドバビブベボヴ':
    HALF[fw] = HALF[unicodedata.normalize('NFD', fw)[0]] + b'\xde'
for fw in 'パピプペポ':
    HALF[fw] = HALF[unicodedata.normalize('NFD', fw)[0]] + b'\xdf'


def enc(s):
    out = b''
    for ch in s:
        if 'ぁ' <= ch <= 'ゖ':
            out += HALF[chr(ord(ch) + 0x60)]
        else:
            out += ch.encode('cp932')
    return out


def dec(b):
    """반각 가타카나 → 히라가나로 읽어 보기(탁음 합침)"""
    s = b.decode('cp932', 'replace')
    out = []
    for ch in s:
        if '｡' <= ch <= 'ﾟ':
            fw = unicodedata.normalize('NFKC', ch)
            if fw in '゙゛' and out:
                out[-1] = unicodedata.normalize('NFC', out[-1] + '゙'); continue
            if fw in '゚゜' and out:
                out[-1] = unicodedata.normalize('NFC', out[-1] + '゚'); continue
            if 'ァ' <= fw <= 'ヶ':
                fw = chr(ord(fw) - 0x60)
            out.append(fw)
        else:
            out.append(ch)
    return ''.join(out)
