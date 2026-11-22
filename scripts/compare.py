#!/usr/bin/env python3
"""把兩張圖用最近鄰整數倍放大後並排，用來放大檢查重繪結果（和原圖、或和既有成品比）。

  python compare.py source.png out/hero_overlay.png --out check/hero_eyes.png --box 200 220 520 360 --scale 6
  python compare.py old/hero_1x.png out/hero_1x.png --out check/hero_vs_old.png --scale 8

--box 是第一張圖上的範圍（x0 y0 x1 y1，px）。兩張圖尺寸相同時，第二張用同一個範圍，並印出完全相同的像素比例；
尺寸不同時（例如 AI 原圖和 _1x）各自放大到差不多的高度並排，--box 只套用在第一張。
"""
import argparse
import os

import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--out', required=True)
    ap.add_argument('--box', type=int, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'))
    ap.add_argument('--scale', type=int, default=0, help='放大倍數（整數）；不給就自動選到高度約 900 px')
    ap.add_argument('--bg', default='#2a2834', help='透明處墊的底色')
    a = ap.parse_args()

    bg = tuple(int(a.bg.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) + (255,)

    def flat(im):
        b = Image.new('RGBA', im.size, bg); b.alpha_composite(im); return b.convert('RGB')

    A = Image.open(a.a).convert('RGBA'); B = Image.open(a.b).convert('RGBA')
    same = A.size == B.size
    if same:
        d = (np.asarray(A) != np.asarray(B)).any(-1)
        print(f'尺寸相同 {A.size[0]}×{A.size[1]}：完全相同的像素 {100 - d.mean() * 100:.2f}%，不同的有 {int(d.sum())} 個')
    if a.box:
        A = A.crop(a.box)
        if same:
            B = B.crop(a.box)
    ka = a.scale or max(1, round(900 / A.height))
    kb = ka if same else max(1, round(A.height * ka / B.height))
    A = flat(A).resize((A.width * ka, A.height * ka), Image.NEAREST)
    B = flat(B).resize((B.width * kb, B.height * kb), Image.NEAREST)
    out = Image.new('RGB', (A.width + B.width + 8, max(A.height, B.height)), (255, 0, 255))
    out.paste(A, (0, 0)); out.paste(B, (A.width + 8, 0))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    out.save(a.out)
    print(f'{a.out}：左 ×{ka}、右 ×{kb}')


if __name__ == '__main__':
    main()
