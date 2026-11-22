#!/usr/bin/env python3
"""第 3 步的準備：把立繪放進和圖表同尺寸的白底畫布，縮到圖表要用的格距，當作給影像模型的參考圖。

  python make_scale_ref.py --portrait out/hero_1x.png --canvas 1536x1024 --rows 2 --cols 6 --out work/hero_scale_ref.png

為什麼要這樣做：直接給放大 10 倍的立繪，模型會照立繪的像素大小畫，圖表塞不下、格距對不上，臉也容易被改畫。
參考圖和要生成的圖表同尺寸、角色大小和像素大小都和圖表裡的小人一樣，模型才會照這個比例畫。

格距（一個像素格在圖表上是幾 px）會取整數：每格（畫布寬 ÷ cols、畫布高 ÷ rows）要放得下一個角色再留邊。
腳本會印出格距和建議的畫格大小，請把它們記到設定檔的 sheet 區段和提示詞裡。
"""
import argparse
import math
import os

import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--portrait', required=True, help='立繪的 _1x.png（一格一像素、背景透明）')
    ap.add_argument('--canvas', required=True, help='要生成的圖表尺寸，例如 1536x1024 或 5504x3072')
    ap.add_argument('--rows', type=int, required=True, help='圖表有幾列')
    ap.add_argument('--cols', type=int, required=True, help='每列幾格')
    ap.add_argument('--pitch', type=int, help='直接指定格距（px，整數）；不給就自動算')
    ap.add_argument('--margin', type=float, default=0.28, help='每格留給動作和間隔的比例（預設 0.28）')
    ap.add_argument('--out', required=True, help='輸出的參考圖（PNG）')
    a = ap.parse_args()

    W, H = (int(v) for v in a.canvas.lower().split('x'))
    src = Image.open(a.portrait).convert('RGBA')
    arr = np.asarray(src)
    ys, xs = np.nonzero(arr[..., 3] > 0)
    src = src.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    cw, ch = src.size
    if os.path.exists(a.out) and os.path.samefile(a.out, a.portrait):
        raise SystemExit('輸出檔不能和立繪是同一個檔案')

    cell_w, cell_h = W / a.cols, H / a.rows
    # 動作會比站姿寬（揮手、跑步），寬度多留一些
    fit = min(cell_h * (1 - a.margin) / ch, cell_w * (1 - a.margin) / (cw * 1.25))
    pitch = a.pitch or int(math.floor(fit))
    if pitch < 3:
        raise SystemExit(f'算出來的格距只有 {fit:.1f} px，太小了，模型畫不出乾淨的像素。'
                         '請加大圖表尺寸，或減少每張圖表的列數／每列格數（分成多張圖表）。')
    if pitch > fit:
        print(f'!! 指定的格距 {pitch} px 比建議值 {fit:.1f} px 大，小人可能會互相碰到')

    big = src.resize((cw * pitch, ch * pitch), Image.NEAREST)
    canvas = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    canvas.alpha_composite(big, ((W - big.width) // 2, (H - big.height) // 2))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    canvas.convert('RGB').save(a.out)

    fw = int(math.ceil(cell_w / pitch / 8) * 8); fh = int(math.ceil((ch + 8) / 8) * 8)
    fw = min(fw, int(math.ceil(cw * 1.8 / 8) * 8))
    print(f'參考圖：{a.out}（{W}×{H}，角色 {cw}×{ch} 格，格距 {pitch} px，角色在圖上高 {ch * pitch} px）')
    print('請記到設定檔的 sheet 區段：')
    print(f'  "pitch": {pitch}, "height_cells": {ch}, "grid": {{"rows": {a.rows}, "cols": {a.cols}}},')
    print(f'  "frame": [{fw}, {fh}], "anchor": [{fw // 2}, {fh - 4}]')
    print('提示詞裡要寫的數字：')
    print(f'  圖表尺寸 {W}×{H}、{a.rows} 列 × {a.cols} 格、站姿高度約 {ch} 個像素格、一個像素格 {pitch}×{pitch} px')


if __name__ == '__main__':
    main()
