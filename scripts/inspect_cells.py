#!/usr/bin/env python3
"""把重繪結果的一塊範圍印成文字圖樣（附格座標和色盤編號），用來寫指定格子的人工修正。

  python inspect_cells.py out/hero_data.npz --box 45 40 85 60                 # 立繪（座標是整張立繪的格子）
  python inspect_cells.py out/hero_grids.npz --frame front --box 20 10 44 30  # 精靈圖的某個畫格（座標是畫格內的格子）
  python inspect_cells.py out/hero_data.npz --box 45 40 85 60 --png check/eyes.png   # 另存放大圖，附格線和座標

--box 是 x0 y0 x1 y1（格子，含 x0、y0，不含 x1、y1）。文字圖樣裡每個字元是一個色盤編號，「.」是透明。
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxlib as px


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('npz', help='redraw_portrait.py 的 _data.npz 或 redraw_sheet.py 的 _grids.npz')
    ap.add_argument('--frame', help='_grids.npz 裡的畫格名稱（不給就列出所有名稱）')
    ap.add_argument('--box', type=int, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'))
    ap.add_argument('--png', help='另存放大圖')
    ap.add_argument('--scale', type=int, default=16)
    a = ap.parse_args()

    d = np.load(a.npz); P = d['P']
    if 'g' in d.files:
        g = d['g']
    else:
        names = [k[2:] for k in d.files if k.startswith('f:')]
        if not a.frame:
            print('畫格：', ', '.join(names)); return
        if a.frame not in names:
            sys.exit(f'沒有畫格 {a.frame!r}。可用的：{", ".join(names)}')
        g = d['f:' + a.frame]
    if not a.box:
        ys, xs = np.nonzero(g >= 0)
        a.box = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
    print(px.text_map(g, P, a.box))
    if a.png:
        x0, y0, x1, y1 = a.box; k = a.scale; pad = 28
        rgba = px.grid_rgba(g[y0:y1, x0:x1], P)
        im = px.on_background(rgba, (120, 120, 130)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST)
        out = Image.new('RGB', (im.width + pad, im.height + pad), (30, 30, 36)); out.paste(im, (pad, pad))
        dr = ImageDraw.Draw(out)
        for x in range(x0, x1 + 1):
            dr.line([(pad + (x - x0) * k, pad), (pad + (x - x0) * k, out.height)], fill=(0, 0, 0) if x % 5 else (0, 255, 255))
            if x % 5 == 0 and x < x1:
                dr.text((pad + (x - x0) * k + 2, 8), str(x), fill=(255, 255, 255))
        for y in range(y0, y1 + 1):
            dr.line([(pad, pad + (y - y0) * k), (out.width, pad + (y - y0) * k)], fill=(0, 0, 0) if y % 5 else (0, 255, 255))
            if y % 5 == 0 and y < y1:
                dr.text((2, pad + (y - y0) * k + 2), str(y), fill=(255, 255, 255))
        os.makedirs(os.path.dirname(os.path.abspath(a.png)), exist_ok=True)
        out.save(a.png); print('放大圖：', a.png)


if __name__ == '__main__':
    main()
