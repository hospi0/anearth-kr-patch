# -*- coding: utf-8 -*-
r"""LZSS 변형 시험기 — GAME.PRG 대사는 LZSS 압축 SJIS 로 보인다(0xB0EBC 부근 «ユキ»·«クガイア» 조각)
  변형: 플래그 비트 순서(LSB/MSB) · 리터럴 비트(1/0) · 참조 꼴(오프셋·길이 배치) · 창 초기 위치
"""
import sys


def prefill():
    """★이 게임의 창 초기값(2026-09-26 RAM 풀린 대본과 대조로 확정) — 일본 게임 흔한 사전 채움:
    0x000‥0xCFF = 0‥255 각 13번 · 0xD00‥0xDFF = 0‥255 · 0xE00‥0xEFF = 255‥0 · 0xF00‥0xF7F = 0 · 0xF80‥0xFFF = 0x20"""
    b = bytearray()
    for i in range(256):
        b += bytes([i]) * 13
    b += bytes(range(256))
    b += bytes(range(255, -1, -1))
    b += bytes(0x80)
    b += b' ' * (4096 - len(b))
    return b


def decode(src, pos, n_out, lsb=True, lit1=True, ref='okumura', init=0xFEE, fill=None, win=4096):
    buf = prefill() if fill is None else bytearray([fill]) * win
    r = init
    out = bytearray()
    flags, nb = 0, 0
    while len(out) < n_out and pos < len(src):
        if nb == 0:
            flags = src[pos]; pos += 1; nb = 8
        bit = (flags & 1) if lsb else (flags >> 7) & 1
        flags = (flags >> 1) if lsb else ((flags << 1) & 0xFF)
        nb -= 1
        if bit == (1 if lit1 else 0):
            if pos >= len(src):
                break
            c = src[pos]; pos += 1
            out.append(c); buf[r] = c; r = (r + 1) % win
        else:
            if pos + 1 >= len(src):
                break
            a, b = src[pos], src[pos + 1]; pos += 2
            if ref == 'okumura':          # a = 오프셋 하위, b 상위4 = 오프셋 상위, b 하위4 = 길이-3
                off = a | ((b & 0xF0) << 4); ln = (b & 0x0F) + 3
            elif ref == 'hi_len':         # a 상위4 = 길이-3
                off = ((a & 0x0F) << 8) | b; ln = (a >> 4) + 3
            elif ref == 'rel':            # 상대 거리(되돌아가기) 12비트 + 길이 4비트
                d = ((a << 8) | b) >> 4; ln = (b & 0x0F) + 3
                off = (r - d - 1) % win
            for k in range(ln):
                c = buf[(off + k) % win]
                out.append(c); buf[r] = c; r = (r + 1) % win
    return bytes(out), pos


def sjis_score(b):
    ok = bad = i = 0
    while i < len(b) - 1:
        x = b[i]
        if 0x81 <= x <= 0x9f or 0xe0 <= x <= 0xef:
            try:
                b[i:i + 2].decode('cp932'); ok += 1
            except UnicodeDecodeError:
                bad += 1
            i += 2
        else:
            i += 1
    return ok / max(1, len(b) / 2)
