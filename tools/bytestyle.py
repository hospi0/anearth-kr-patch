# -*- coding: utf-8 -*-
r"""원문 바이트 모양 — 1바이트 반각 글자(0xA1‥0xDF)가 하나라도 있나
  ★2026-09-27 상점 메뉴 «산?/판?»: 원문이 전부 2바이트 SJIS 인 문자열은 2바이트 전용 렌더러로 그려진다(1바이트 한글이 다음 바이트와 짝지어 깨짐)
   → 원문에 1바이트 글자가 없으면 번역도 2바이트만(kenc sjis_only).
"""
import re


def has_one_byte(raw):
    i = 0
    while i < len(raw):
        x = raw[i]
        if (0x81 <= x <= 0x9F or 0xE0 <= x <= 0xEF) and i + 1 < len(raw):
            i += 2; continue
        if x == 0x25:                                   # 제어 %op + 인수는 건너뛴다(대본 조각 안)
            i += 2; continue
        if 0xA1 <= x <= 0xDF:
            return True
        i += 1
    return False


def has_kana_text(raw):
    """글자(한자·가나) 가 있는 조각인가 — 영문·숫자뿐이면 판단 안 함"""
    return any((0x81 <= x <= 0x9F or 0xE0 <= x <= 0xEF) for x in raw)
