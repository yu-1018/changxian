#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 512x512 的 solo-loop 图标（纯标准库，无第三方依赖）。"""
import math
import struct
import zlib

W = H = 512
SS = 2                      # 超采样倍率（抗锯齿）
W2, H2 = W * SS, H * SS

BG_TOP = (11, 18, 32)
BG_BOT = (20, 33, 61)
CYAN = (34, 211, 238)
VIOLET = (129, 140, 248)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


# ---------- 1) 背景渐变 ----------
buf = bytearray(W2 * H2 * 3)
for y in range(H2):
    c = lerp(BG_TOP, BG_BOT, y / (H2 - 1))
    row = bytes(c) * W2
    buf[y * W2 * 3:(y + 1) * W2 * 3] = row

# ---------- 2) 光晕层（较宽的弧，低亮度） ----------
glow = bytearray(W2 * H2)  # 亮度叠加


def stamp(layer, cx, cy, r, val, additive=True):
    x0, x1 = max(0, int(cx - r) - 1), min(W2 - 1, int(cx + r) + 1)
    y0, y1 = max(0, int(cy - r) - 1), min(H2 - 1, int(cy + r) + 1)
    r2 = r * r
    for y in range(y0, y1 + 1):
        dy = y + 0.5 - cy
        base = y * W2
        for x in range(x0, x1 + 1):
            dx = x + 0.5 - cx
            d2 = dx * dx + dy * dy
            if d2 <= r2:
                i = base + x
                if additive:
                    layer[i] = min(255, layer[i] + val)
                else:
                    layer[i] = val


def lemniscate(n, a, cx, cy):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        s = math.sin(t)
        den = 1 + s * s
        pts.append((cx + a * math.cos(t) / den, cy + a * s * math.cos(t) / den))
    return pts


A = 150 * SS
CX, CY = W2 / 2, H2 / 2
curve = lemniscate(3000, A, CX, CY)
step = max(1, len(curve) // 1400)

# 光晕
for p in curve[::step]:
    stamp(glow, p[0], p[1], 17 * SS / 2, 26)
# 主线
line = bytearray(W2 * H2)
for p in curve[::step]:
    stamp(line, p[0], p[1], 8.5 * SS / 2, 255)

# ---------- 3) 合成 ----------
out = bytearray(W2 * H2 * 3)
for i in range(W2 * H2):
    r = buf[i * 3]
    g = buf[i * 3 + 1]
    b = buf[i * 3 + 2]
    gl = glow[i]
    if gl:
        r = min(255, r + gl // 3)
        g = min(255, g + gl)
        b = min(255, b + int(gl * 1.15))
    if line[i]:
        r, g, b = CYAN
    out[i * 3] = r
    out[i * 3 + 1] = g
    out[i * 3 + 2] = b

# ---------- 4) 降采样写 PNG ----------
rows = bytearray()
for y in range(H):
    rows.append(0)
    yb = y * SS
    for x in range(W):
        xb = x * SS
        ar = ag = ab = 0
        for dy in range(SS):
            base = ((yb + dy) * W2 + xb) * 3
            for dx in range(SS):
                o = base + dx * 3
                ar += out[o]
                ag += out[o + 1]
                ab += out[o + 2]
        n = SS * SS
        rows += bytes((ar // n, ag // n, ab // n))


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
       + chunk(b"IEND", b""))

open("expert.png", "wb").write(png)
print("wrote expert.png", len(png), "bytes")
