#!/usr/bin/env python3
"""第 4 步（精靈圖表）：把 AI 生成的精靈圖表切出每個小人，照網格重繪後排進固定畫格。

  python redraw_sheet.py --config character.json --out out/
  python redraw_sheet.py --config character.json --out out/ --extract-only   # 只切圖，先確認每個小人都切對
  python redraw_sheet.py --config character.json --out out/ --reuse          # 只重套人工修正和排版

流程：依設定檔的區塊切出小人 → 決定每個區塊的格距（統一角色高度）→ 逐個小人搜尋格線起點並取樣
→ 所有小人共用一份色盤 → 排進固定畫格、對齊錨點 → 指定格子的人工修正 → 輸出。
輸出（都在 --out 裡，只寫這幾個檔和 frames_raw/ 裡的同名檔，不會刪除其他東西）：
  <name>_extract_check.png  來源圖表上畫出每個小人的範圍和名稱（先看這張確認切圖）
  <name>_frames.png         所有畫格排成一張（每個區塊一列），另有 _frames_4x.png
  <name>_frames.json        畫格位置、畫格大小、錨點、色盤、每個區塊的格距
  <name>_grids.npz          P 色盤、每個畫格的色盤編號陣列（鍵是 f:<畫格名稱>，-1 透明）
  <name>_sprites_raw.npz    取樣後、排版前的小人（--reuse 用）
  frames_raw/<畫格>.png     單格 PNG
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxlib as px


# ---------- 切出小人 ----------

def section_box(sec, sheet, W, H):
    if 'box' in sec:
        return [int(v) for v in sec['box']]
    if 'row' in sec:
        rows = sheet['grid']['rows']
        return [0, int(round(H * sec['row'] / rows)), W, int(round(H * (sec['row'] + 1) / rows))]
    raise SystemExit(f"區塊 {sec['name']} 要有 box（[x0, y0, x1, y1]）或 row（搭配 sheet.grid.rows）")


def section_names(sec):
    if 'names' in sec:
        return list(sec['names'])
    return [f"{sec['name']}_{i}" for i in range(sec['count'])]


def extract(a, fg, sheet, sections, draw):
    """在每個區塊裡用連通區域切出小人；黏在一起的依寬度切開。回傳 {名稱: dict(box, mask, sec)}。"""
    H, W = fg.shape
    it = max(1, round(W / 1536))
    min_px = sheet.get('min_pixels', 0.0016 * W * H)
    sprites = {}
    for sec in sections:
        x0, y0, x1, y1 = section_box(sec, sheet, W, H)
        names = section_names(sec); N = len(names)
        m = fg[y0:y1, x0:x1]
        lab, _ = ndi.label(ndi.binary_dilation(m, iterations=it), structure=np.ones((3, 3)))
        comps = []
        for i, sl in enumerate(ndi.find_objects(lab)):
            if ((lab[sl] == i + 1) & m[sl]).sum() < min_px:
                continue          # 動作線、說明文字等小東西
            comps.append([sl[1].start, sl[0].start, sl[1].stop, sl[0].stop, i + 1])
        comps.sort()
        if not comps:
            raise SystemExit(f"區塊 {sec['name']} 裡找不到小人，請檢查 box 和 background 設定")
        u = sum(c[2] - c[0] for c in comps) / N
        parts = []
        for c in comps:
            k = max(1, round((c[2] - c[0]) / u)); cm = (lab == c[4]) & m
            if k == 1:
                parts.append(cm); continue
            proj = cm.sum(0); w = (c[2] - c[0]) / k; cuts = [c[0]]
            for j in range(1, k):
                t = int(c[0] + w * j); r = int(0.22 * w); xs = np.arange(t - r, t + r)
                cuts.append(int(xs[np.argmin(proj[xs] + 0.02 * np.abs(xs - t))]))
            cuts.append(c[2])
            for j in range(k):
                mm = np.zeros_like(cm); mm[:, cuts[j]:cuts[j + 1]] = cm[:, cuts[j]:cuts[j + 1]]
                l2, k2 = ndi.label(mm, structure=np.ones((3, 3)))
                if k2 > 1:        # 切開後只留最大的一塊
                    mm = l2 == (1 + int(np.argmax(ndi.sum(mm, l2, range(1, k2 + 1)))))
                parts.append(mm)
        if len(parts) != N:
            print(f"!! 區塊 {sec['name']}：切出 {len(parts)} 個小人，設定檔寫的是 {N} 個。請看 extract_check 圖調整 box、names 或 min_pixels")
        draw.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(90, 140, 255))
        for mm, name in zip(parts, names):
            if name in sprites:
                raise SystemExit(f'小人名稱重複：{name}')
            ys, xs = np.nonzero(mm)
            bx = (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1)
            sprites[name] = dict(box=bx, mask=mm[ys.min():ys.max() + 1, xs.min():xs.max() + 1], sec=sec['name'])
            draw.rectangle(bx, outline=(0, 255, 0)); draw.text((bx[0] + 1, max(0, bx[1] - 11)), name, fill=(255, 200, 0))
    return sprites


# ---------- 取樣 ----------

def head_width(M, frac=0.45):
    """小人上方 frac 高度內最寬的一列有幾 px（用來讓不同區塊的頭一樣大）。"""
    r = M[:max(1, int(M.shape[0] * frac))]
    w = [np.nonzero(x)[0] for x in r]
    return max((x.max() - x.min() + 1) for x in w if len(x))


def phase_variance(im, M, p, ox, oy):
    """格線起點 (ox, oy) 時，前景像素在各格內的顏色變異總和（向量化，用來搜尋起點）。"""
    H, W = M.shape
    ex = np.unique(np.clip(np.ceil(np.arange(ox - p, W + p, p)), 0, W).astype(int))
    ey = np.unique(np.clip(np.ceil(np.arange(oy - p, H + p, p)), 0, H).astype(int))
    red = lambda v: np.add.reduceat(np.add.reduceat(v, ey[:-1], axis=0), ex[:-1], axis=1)
    Mf = M.astype(np.float64)
    n = red(Mf); s = red(im * Mf[..., None]); s2 = red((im ** 2) * Mf[..., None]).sum(-1)
    area = np.diff(ey)[:, None] * np.diff(ex)[None, :]
    ok = (n / area >= 0.3) & (n > 1)
    return float((s2[ok] - (s[ok] ** 2).sum(-1) / n[ok]).sum())


def sample(im, M, p, ox, oy, margin=0.27):
    """每一格取中央部分的平均色（避開格子邊緣的雜色）。回傳 (顏色, 前景覆蓋率)。"""
    H, W = M.shape
    ex = np.arange(ox - p, W + p, p); ey = np.arange(oy - p, H + p, p)
    nx, ny = len(ex) - 1, len(ey) - 1
    col = np.zeros((ny, nx, 3), np.float32); cov = np.zeros((ny, nx), np.float32)
    for j in range(ny):
        y0 = max(0, math.ceil(ey[j])); y1 = min(H, math.ceil(ey[j + 1]))
        if y1 <= y0:
            continue
        cy0 = max(0, min(H - 1, int(round(ey[j] + margin * p)))); cy1 = max(cy0 + 1, min(H, int(round(ey[j + 1] - margin * p))))
        for i in range(nx):
            x0 = max(0, math.ceil(ex[i])); x1 = min(W, math.ceil(ex[i + 1]))
            if x1 <= x0:
                continue
            c = M[y0:y1, x0:x1].mean(); cov[j, i] = c
            if c < 0.3:
                continue
            cx0 = max(0, min(W - 1, int(round(ex[i] + margin * p)))); cx1 = max(cx0 + 1, min(W, int(round(ex[i + 1] - margin * p))))
            col[j, i] = im[cy0:cy1, cx0:cx1].reshape(-1, 3).mean(0)
    return col, cov


def section_pitches(sheet, sections, sprites, im):
    """每個區塊在來源圖上一格是幾 px。

    scale 的寫法：
      "height"                    這個區塊的小人是完整站姿：格距 = 小人高度的中位數 ÷ height_cells
                                  （加 "scale_sprite": "front" 則只看那一個小人）
      {"head_of": "turn"}         姿勢不是站直的區塊：用頭部寬度和另一個區塊對齊（頭一樣大）
                                  半身或只有頭的區塊再加 "head_frac": 1.0
      數字                         直接指定格距（px）
    區塊沒寫 scale 時用 sheet.pitch：數字是整張圖表共用的格距，"auto" 是自動量。
    """
    HT = sheet.get('height_cells', 50)
    by = {s['name']: s for s in sections}
    members = lambda s: [sprites[n] for n in section_names(s) if n in sprites]
    hw = lambda s: (head_width(sprites[s['scale_sprite']]['M'], s.get('head_frac', 0.45)) if s.get('scale_sprite') in sprites
                    else float(np.median([head_width(m['M'], s.get('head_frac', 0.45)) for m in members(s)])))
    default = sheet.get('pitch')
    if default == 'auto':
        lo, hi = sheet.get('pitch_range', [3.0, 40.0])
        ex, ey = px.estimate_pitch(im, lo, hi, hint=sheet.get('pitch_hint'), log=print)
        default = (ex + ey) / 2
        print(f'自動量到的格距：x {ex:.3f}、y {ey:.3f} px（用 {default:.3f}）')
    out = {}

    def get(name, depth=0):
        if name in out:
            return out[name]
        s = by[name]; sc = s.get('scale', default if default is not None else 'height')
        if isinstance(sc, (int, float)):
            p = float(sc)
        elif sc == 'height':
            ms = [sprites[s['scale_sprite']]] if s.get('scale_sprite') in sprites else members(s)
            p = float(np.median([m['M'].shape[0] for m in ms])) / HT
        elif isinstance(sc, dict) and 'head_of' in sc:
            if depth > 8:
                raise SystemExit('scale 的 head_of 互相參照了')
            ref = by[sc['head_of']]
            s2 = dict(s); s2.setdefault('head_frac', sc.get('head_frac', 0.45))
            p = float(get(ref["name"], depth + 1) * hw(s2) / hw(ref))
        else:
            raise SystemExit(f"區塊 {name} 的 scale 看不懂：{sc}")
        out[name] = p
        return p

    for s in sections:
        get(s['name'])
    return out


# ---------- 排進畫格 ----------

def place(g, FW, FH, AX, BASE, align='head', lift=0):
    """把小人放進畫格：頭部中心對齊 x=AX、腳底對齊 y=BASE（lift 是離地格數）。回傳 (畫格, 是否被裁掉)。"""
    h, w = g.shape; fg = g >= 0
    cx = w / 2 if align == 'center' else np.nonzero(fg[:max(1, int(h * 0.45))])[1].mean() + 0.5
    x = int(round(AX - cx)); y = BASE - lift - h
    fr = np.full((FH, FW), -1, np.int16)
    clipped = x < 0 or y < 0 or x + w > FW or y + h > FH
    x = max(0, min(FW - w, x)) if w <= FW else 0
    y = max(0, y)
    hh, ww = min(h, FH - y), min(w, FW - x)
    fr[y:y + hh, x:x + ww] = g[:hh, :ww]
    return fr, clipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True, help='角色設定檔（JSON），用裡面的 sheet 區段')
    ap.add_argument('--out', required=True, help='輸出資料夾')
    ap.add_argument('--name', help='輸出檔名的前綴（預設用設定檔的 name）')
    ap.add_argument('--extract-only', action='store_true', help='只切圖並輸出 extract_check 圖')
    ap.add_argument('--reuse', action='store_true', help='沿用上次的 <name>_sprites_raw.npz，只重做排版和人工修正')
    a = ap.parse_args()

    cfg = px.load_config(a.config)
    sheet = cfg.get('sheet') or sys.exit('設定檔沒有 sheet 區段')
    name = a.name or cfg.get('name') or 'character'
    sections = sheet['sections']
    FW, FH = sheet.get('frame', [64, 64]); AX, BASE = sheet.get('anchor', [FW // 2, FH - 2])
    sources = sorted({px.resolve(cfg, s.get('source', sheet.get('source'))) for s in sections})
    P_ = lambda f: px.out_path(a.out, f'{name}_{f}', sources)
    raw_path = P_('sprites_raw.npz')

    if a.reuse and os.path.exists(raw_path):
        d = np.load(raw_path, allow_pickle=False)
        P = d['P']; meta_raw = json.loads(str(d['meta']))
        grids = {k[2:]: d[k] for k in d.files if k.startswith('g:')}
        print(f'沿用 {raw_path}（{len(grids)} 個小人，{len(P)} 色）')
    else:
        raw = {}; meta_raw = {'pitch': {}, 'sprites': {}}
        for si, src in enumerate(sources):
            secs = [s for s in sections if px.resolve(cfg, s.get('source', sheet.get('source'))) == src]
            im = px.load_rgb(src)
            bg = px.background_color(im, sheet.get('background', 'auto'))
            tol = sheet.get('bg_tolerance', 70)
            dev = np.abs(im - bg).sum(2)
            fg = dev > tol
            vis = Image.open(src).convert('RGB'); draw = ImageDraw.Draw(vis)
            sp = extract(im, fg, sheet, secs, draw)
            vis.save(P_('extract_check.png' if len(sources) == 1 else f'extract_check_{si + 1}.png'))
            print(f'{os.path.basename(src)}：切出 {len(sp)} 個小人')
            if a.extract_only:
                continue
            keep = sheet.get('enclosed', 'auto') == 'keep'
            for s in sp.values():
                x0, y0, x1, y1 = s['box']; M = s['mask']
                hole = ndi.binary_fill_holes(M) & ~M
                # 被輪廓包住、顏色接近背景的區域：預設只留和背景有一點差異的；"enclosed": "keep" 則全部留下
                s['M'] = M | (hole if keep else hole & (dev[y0:y1, x0:x1] > tol * 18 / 70))
            pitches = section_pitches(sheet, secs, sp, im)
            print('  格距（px）：', {k: round(v, 2) for k, v in pitches.items()})
            for nm, s in sp.items():
                p = pitches[s['sec']]; x0, y0, x1, y1 = s['box']; M = s['M']; crop = im[y0:y1, x0:x1]
                st = max(1, int(p // 4)) if p > 5 else 1
                best = min((phase_variance(crop, M, p, ox, oy), ox, oy) for oy in np.arange(0, p, st) for ox in np.arange(0, p, st))
                col, cov = sample(crop, M, p, best[1], best[2])
                raw[nm] = (col, cov >= 0.5, cov >= 0.97, bg)
                meta_raw['sprites'][nm] = {'section': s['sec'], 'source_box': [int(v) for v in s['box']], 'pitch': round(p, 4)}
            meta_raw['pitch'].update({k: round(v, 4) for k, v in pitches.items()})
        if a.extract_only:
            print('只切圖。確認 extract_check 圖上每個小人的範圍和名稱都對，再拿掉 --extract-only。')
            return

        # 同一位角色的所有小人共用一份色盤
        allc = np.concatenate([r[0][r[2]] for r in raw.values()])
        P = px.merged_palette(allc, **sheet.get('palette_options', {}))
        if sheet.get('palette_from'):
            base = px.read_palette(px.resolve(cfg, sheet['palette_from']))
            n0 = len(P)
            P, _ = px.snap_palette(P, base, sheet.get('palette_snap', 30))
            nb = sum(1 for c in P if (np.abs(base - c).sum(1) < 1).any())
            print(f'色盤對到既有色盤：{n0} 色 → {len(P)} 色（沿用 {nb} 色、新增 {len(P) - nb} 色）')
        grids = {}
        for nm, (col, fgm, full, bgc) in raw.items():
            fringe = sheet.get('trim_fringe', 0)
            if fringe:      # 輪廓外側的殘影：貼著透明區、顏色接近背景的格子去掉
                fgm = fgm.copy()
                near_bg = np.abs(col - bgc).sum(-1) < fringe
                for _ in range(2):
                    fgm &= ~(near_bg & ndi.binary_dilation(~np.pad(fgm, 1))[1:-1, 1:-1])
                full = full & fgm
            g = ((col[:, :, None, :] - P[None, None]) ** 2).sum(-1).argmin(-1); g[~fgm] = -1
            for j, i in zip(*np.nonzero(fgm & ~full)):      # 邊緣覆蓋不滿的格子借用鄰格的顏色
                nb = [(b, q) for q, b in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1))
                      if 0 <= q < g.shape[1] and 0 <= b < g.shape[0] and full[b, q]]
                if nb:
                    dd = [((col[j, i] - P[g[b, q]]) ** 2).sum() for b, q in nb]; b, q = nb[int(np.argmin(dd))]; g[j, i] = g[b, q]
            ys, xs = np.nonzero(g >= 0)
            g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            if sheet.get('remove_specks'):
                g = px.remove_specks(g, P)
            grids[nm] = g.astype(np.int16)
        np.savez_compressed(raw_path, P=P, meta=json.dumps(meta_raw), **{'g:' + k: v for k, v in grids.items()})

    # 排進固定畫格、對齊錨點
    cols = sheet.get('columns', max(len(section_names(s)) for s in sections))
    frames = {}; info = {}; sec_frames = {}; row = 0
    fixes = sheet.get('fixes', {})
    for s in sections:
        names = [n for n in section_names(s) if n in grids]
        bottoms = {n: meta_raw['sprites'][n]['source_box'][3] for n in names}
        for k, n in enumerate(names):
            lift = 0
            if s.get('keep_lift'):     # 跑步離地的畫格保留離地高度
                lift = int(round((max(bottoms.values()) - bottoms[n]) / meta_raw['sprites'][n]['pitch']))
            fr, clipped = place(grids[n], FW, FH, AX, BASE, s.get('align', 'head'), lift)
            if clipped:
                print(f'!! {n} 放不進 {FW}×{FH} 的畫格（小人 {grids[n].shape[1]}×{grids[n].shape[0]} 格），被裁掉了。請加大 frame。')
            if n in fixes:
                fr, P, _ = px.apply_fixes(fr, P, fixes[n])
            frames[n] = fr
            info[n] = {'x': (k % cols) * FW, 'y': (row + k // cols) * FH, 'w': FW, 'h': FH, 'section': s['name']}
        sec_frames[s['name']] = names
        row += max(1, math.ceil(len(names) / cols))
    unknown = set(fixes) - set(frames)
    if unknown:
        print('!! fixes 裡有不存在的畫格名稱：', sorted(unknown))

    sheet_img = np.zeros((FH * row, FW * cols, 4), np.uint8)
    os.makedirs(os.path.join(a.out, 'frames_raw'), exist_ok=True)
    for n, fr in frames.items():
        rgba = px.grid_rgba(fr, P); i = info[n]
        sheet_img[i['y']:i['y'] + FH, i['x']:i['x'] + FW] = rgba
        Image.fromarray(rgba).save(os.path.join(a.out, 'frames_raw', n + '.png'))
    px.save_scaled(sheet_img, P_('frames.png'))
    px.save_scaled(sheet_img, P_('frames_4x.png'), 4)
    heights = {n: int(np.ptp(np.nonzero((f >= 0).any(1))[0]) + 1) for n, f in frames.items()}
    json.dump({
        'meta': {'image': f'{name}_frames.png', 'frame_size': [FW, FH], 'anchor': [AX, BASE],
                 'anchor_note': 'x 是頭部中心，y 是腳底的地面線',
                 'character_height_cells': sheet.get('height_cells', 50),
                 'section_pitch_px': meta_raw['pitch'],
                 'palette': [px.rgb2hex(c) for c in P]},
        'sections': sec_frames, 'frames': info, 'frame_height_cells': heights,
    }, open(P_('frames.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    np.savez_compressed(P_('grids.npz'), P=P, **{'f:' + k: v for k, v in frames.items()})
    for s in sections:
        hs = [heights[n] for n in sec_frames[s['name']]]
        print(f"  {s['name']}：{len(hs)} 格，高度 {min(hs)}–{max(hs)} 格")
    print(f'{name}：{len(frames)} 個畫格，色盤 {len(P)} 色 → {P_("frames.png")}')
    print(f'請放大檢查 {P_("frames_4x.png")}（眼睛、手、腳，以及兩腿之間有沒有殘留的背景）')


if __name__ == '__main__':
    main()
