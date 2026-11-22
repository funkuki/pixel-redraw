#!/usr/bin/env python3
"""第 4 步（立繪）：把 AI 生成的像素風立繪照網格重繪成真正的像素圖。

  python redraw_portrait.py --config character.json --out out/
  python redraw_portrait.py --source portrait.png --name hero --out out/      # 不用設定檔
  python redraw_portrait.py --config character.json --out out/ --reuse        # 只重套人工修正

流程：找網格 → 取色盤 → 一格一色 → 清雜點 → 去背 → 指定格子的人工修正 → 輸出。
輸出（都在 --out 裡，只寫這幾個檔，不會刪除其他東西）：
  <name>_1x.png        一格一像素，背景透明
  <name>_10x.png       最近鄰放大 10 倍
  <name>_overlay.png   貼回原圖網格位置（和原圖同尺寸，方便疊圖對照）
  <name>_compare.png   原圖和重繪並排
  <name>_grid_check.png 原圖中央放大並畫上格線（確認格距有沒有找對）
  <name>_data.npz      g 格子的色盤編號（-1 透明）、P 色盤、ex/ey 格線位置、raw 修正前的格子
  <name>_portrait.json 尺寸、格距、色盤
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxlib as px


def cell_labels(lab, ex, ey, n):
    """每一格取格內最多像素所屬的色盤顏色。"""
    ny, nx = len(ey) - 1, len(ex) - 1
    g = np.zeros((ny, nx), int)
    for j in range(ny):
        for i in range(nx):
            g[j, i] = np.bincount(lab[ey[j]:ey[j + 1], ex[i]:ex[i + 1]].ravel(), minlength=n).argmax()
    return g


def clean_isolated(g, lab, ex, ey, n, keep_ratio=0.7, passes=2):
    """孤立的單格（上下左右都沒有同色）如果在原圖裡佔不到 keep_ratio，就換成鄰近的顏色。"""
    ny, nx = g.shape
    fixed = 0
    for _ in range(passes):
        g0 = g.copy()
        for j in range(ny):
            for i in range(nx):
                nb = [g0[b, a] for a, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)) if 0 <= a < nx and 0 <= b < ny]
                if g0[j, i] in nb:
                    continue
                c = np.bincount(lab[ey[j]:ey[j + 1], ex[i]:ex[i + 1]].ravel(), minlength=n).astype(float)
                if c[g0[j, i]] / c.sum() >= keep_ratio:
                    continue
                g[j, i] = max(set(nb), key=lambda l: (c[l], nb.count(l)))
                fixed += 1
    return g, fixed


def remove_background(g, P, bg, mode='border', holes=(), keep_largest=False):
    """把背景色的格子設成透明。

    mode='border'：只去掉和畫面邊緣相連的（角色身上可以有和背景同色的格子，例如白底上的白襯衫）。
    mode='all'：背景色的格子全部去掉（背景色沒有用在角色身上時最乾淨，被輪廓包住的背景也會一起去掉）。
    holes：mode='border' 時，被輪廓包住的背景（格座標 [x, y]）從這些格子往外填成透明。
    keep_largest：只留最大的一塊，丟掉飄在角色外面的零星格子。
    """
    bi = int(np.linalg.norm(P - bg, axis=1).argmin())
    out = g.copy()
    if mode == 'all':
        out[g == bi] = -1
    else:
        lab, _ = ndi.label(g == bi)
        border = (set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])) - {0}
        out[np.isin(lab, list(border))] = -1
        for x, y in holes:
            l2, _ = ndi.label(g == g[y, x])
            out[l2 == l2[y, x]] = -1
    if keep_largest:
        l3, n = ndi.label(out >= 0, structure=np.ones((3, 3)))
        if n > 1:
            out[l3 != 1 + int(np.argmax(ndi.sum(out >= 0, l3, range(1, n + 1))))] = -1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', help='角色設定檔（JSON），用裡面的 portrait 區段')
    ap.add_argument('--source', help='AI 原圖（沒有設定檔時用）')
    ap.add_argument('--name', help='輸出檔名的前綴（預設用設定檔的 name）')
    ap.add_argument('--out', required=True, help='輸出資料夾')
    ap.add_argument('--reuse', action='store_true', help='沿用上次的 <name>_data.npz，只重做去背和人工修正')
    ap.add_argument('--scale', type=int, default=10, help='放大檔的倍數（整數，預設 10）')
    a = ap.parse_args()

    cfg = px.load_config(a.config) if a.config else {'_dir': os.getcwd()}
    pc = dict(cfg.get('portrait', {}))
    src = px.resolve(cfg, a.source or pc.get('source') or sys.exit('要有 --source 或設定檔的 portrait.source'))
    name = a.name or cfg.get('name') or os.path.splitext(os.path.basename(src))[0]
    im = px.load_rgb(src)
    H, W, _ = im.shape
    P_ = lambda f: px.out_path(a.out, f'{name}_{f}', [src])
    data_path = P_('data.npz')

    if a.reuse and os.path.exists(data_path):
        d = np.load(data_path)
        raw, P, ex, ey = d['raw'], d['P'], d['ex'], d['ey']
        pitch = [float(np.median(np.diff(ex))), float(np.median(np.diff(ey)))]
        print(f'沿用 {data_path}（{raw.shape[1]}×{raw.shape[0]} 格，{len(P)} 色）')
    else:
        # 1. 找網格
        if 'pitch' in pc:
            p = pc['pitch']; pxx, pyy = (p, p) if np.isscalar(p) else p
            if 'origin' in pc:
                phx, phy = pc['origin']
            else:   # 格距固定，只搜尋起點
                pxx, phx, pyy, phy, _ = px.search_grid(im, (pxx, pyy), (pxx, pyy), log=print)
        else:
            if 'pitch_range' in pc:
                r = pc['pitch_range']
                lo, hi = (r[0], r[1]) if np.isscalar(r[0]) else ((r[0][0], r[1][0]), (r[0][1], r[1][1]))
            else:
                ex0, ey0 = px.estimate_pitch(im, hint=pc.get('pitch_hint'), log=print)
                print(f'粗估格距 x {ex0:.2f}、y {ey0:.2f} px')
                lo, hi = (ex0 * 0.95, ey0 * 0.95), (ex0 * 1.05, ey0 * 1.05)
            pxx, phx, pyy, phy, err = px.search_grid(im, lo, hi, log=print)
        ex, ey = px.edges(pxx, phx, W), px.edges(pyy, phy, H)
        pitch = [pxx, pyy]
        print(f'網格：x 格距 {pxx:.2f}、y 格距 {pyy:.2f} px，{len(ex) - 1}×{len(ey) - 1} 格')
        px.grid_overlay(im, ex, ey, P_('grid_check.png'))
        print(f'先看 {P_("grid_check.png")}：青色格線要貼著每個像素的邊。一格裡有 2×2 個像素就是格距大了一倍，'
              '請在設定檔的 portrait 加 pitch_hint（大概的格距）重跑。')

        # 2. 取色盤
        P = px.flat_palette(im, pxx * pyy, **pc.get('palette_options', {}))
        lab = ((im[:, :, None, :] - P[None, None]) ** 2).sum(-1).argmin(-1)
        # 3. 一格一色  4. 清雜點
        raw = cell_labels(lab, ex, ey, len(P))
        raw, nfix = clean_isolated(raw, lab, ex, ey, len(P), pc.get('keep_ratio', 0.7))
        print(f'色盤 {len(P)} 色，清掉 {nfix} 個孤立的雜點')

    # 5. 去背  6. 人工修正
    g = raw.copy()
    bg = px.background_color(im, pc.get('background', 'auto'))
    mode = pc.get('remove_background', 'border')
    if mode:
        g = remove_background(g, P, bg, 'border' if mode is True else mode, pc.get('holes', []), pc.get('keep_largest', False))
    g, P, nedit = px.apply_fixes(g, P, pc.get('fixes'))
    if nedit:
        print(f'人工修正 {nedit} 格')

    # 輸出
    np.savez(data_path, g=g, raw=raw, P=P, ex=ex, ey=ey)
    rgba = px.grid_rgba(g, P)
    px.save_scaled(rgba, P_('1x.png'))
    px.save_scaled(rgba, P_(f'{a.scale}x.png'), a.scale)
    rec = np.zeros((H, W, 4), np.uint8)
    for j in range(g.shape[0]):
        for i in range(g.shape[1]):
            rec[ey[j]:ey[j + 1], ex[i]:ex[i + 1]] = rgba[j, i]
    Image.fromarray(rec).save(P_('overlay.png'))
    flat = np.asarray(px.on_background(rec, tuple(int(v) for v in bg))).astype(np.float32)
    diff = float(np.abs(flat - im).mean())
    side = Image.new('RGB', (W * 2, H))
    side.paste(Image.fromarray(im.astype(np.uint8)), (0, 0)); side.paste(Image.fromarray(flat.astype(np.uint8)), (W, 0))
    k = max(1, round(2400 / side.width))
    side.resize((side.width * k, side.height * k), Image.NEAREST).save(P_('compare.png'))

    ys, xs = np.nonzero(g >= 0)
    used = np.unique(g[g >= 0])
    info = {
        'name': name, 'source': os.path.basename(src), 'canvas_cells': [int(g.shape[1]), int(g.shape[0])],
        'character_cells': [int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)],
        'character_box': [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
        'cell_px_in_source': [round(pitch[0], 3), round(pitch[1], 3)],
        'palette': [px.rgb2hex(P[i]) for i in used],
        'palette_index': [int(i) for i in used],
    }
    json.dump(info, open(P_('portrait.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f"{name}：畫布 {g.shape[1]}×{g.shape[0]} 格，角色 {info['character_cells'][0]}×{info['character_cells'][1]} 格，"
          f"{len(used)} 色，和原圖的平均色差 {diff:.2f}")
    print(f'請放大檢查 {P_("compare.png")}（眼睛、手、腳最容易出錯）')


if __name__ == '__main__':
    main()
