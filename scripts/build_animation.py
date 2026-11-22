#!/usr/bin/env python3
"""第 5 步：把畫格排成動作、設定速度、鏡射出向左的畫格，輸出精靈圖表、GIF 和預覽頁。

  python build_animation.py --config character.json --frames out/ --out out/

--frames 是 redraw_sheet.py 的輸出資料夾（讀裡面的 <name>_grids.npz 和 <name>_frames.json）。
設定檔的 animations 是一個清單，每個動作一列，依序排進圖表。每個動作用下列其中一種方式指定畫格：
  {"name": "walk_right", "section": "walk", "frame_ms": 100}        整個區塊依序當成一個循環動畫
  {"name": "turnaround", "frames": ["front", "side", "back"], "frame_ms": 400}   指定畫格
  {"name": "walk_left", "mirror": "walk_right"}                      左右鏡射另一個動作（速度沿用）
  {"name": "walk_down", "step": {"base": "front", "cycle": "walk"}, "frame_ms": 100}
        用一張正面或背面站姿做出簡化的原地踏步：輪流抬腳加身體起伏（cycle 是 walk 或 run；
        背面加 "swap_sides": true）。這是沒有該方向參考圖時的替代方案，不如重繪的畫格自然。
frame_ms 是每格的毫秒數；0 或不寫表示這一列是單張姿勢（表情、動作），不是動畫。"loop": false 可關掉循環。
沒有寫 animations 時，每個區塊各成一列（用區塊的 frame_ms）。

輸出（都在 --out 裡，只寫這幾個檔和 frames/、gif/ 裡的同名檔，不會刪除其他東西）：
  <name>_sheet.png、<name>_sheet_4x.png   最終精靈圖表（每個動作一列）
  <name>_sheet.json                        畫格位置、動作、速度、錨點、色盤
  frames/<畫格>.png                        單格 PNG
  gif/<動作>.gif                           每個動畫一個 GIF（最近鄰放大、顏色和圖表完全相同）
  <name>_preview.html                      可以直接用瀏覽器打開的預覽頁（圖表和資料都內嵌在檔案裡）
"""
import argparse
import base64
import io
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pxlib as px
from redraw_sheet import place

# 簡化踏步的格式：(抬哪隻腳, 抬高幾格, 身體下沉幾格；負數是整個人離地)
CYCLES = {
    'walk': [(None, 0, 1), ('L', 1, 0), ('L', 3, 0), ('L', 1, 0), (None, 0, 1), ('R', 1, 0), ('R', 3, 0), ('R', 1, 0)],
    'run': [(None, 0, 2), ('L', 3, 0), ('L', 4, -1), (None, 0, 2), ('R', 3, 0), ('R', 4, -1)],
}


def crop(fr):
    ys, xs = np.nonzero(fr >= 0)
    return fr[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def legzone(g):
    """從腳底往上數，兩腿分開的列數，以及兩腿之間的分界欄。"""
    h, w = g.shape; z = 0
    for j in range(h - 1, max(h - 14, -1), -1):
        xs = np.nonzero(g[j] >= 0)[0]
        runs = np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1)
        if len(runs) >= 2:
            z += 1
        else:
            break
    bx = np.nonzero((g[h - 3:] >= 0).any(0))[0]; cx = (bx.min() + bx.max() + 1) // 2
    if z >= 3:
        xs = np.nonzero(g[h - 2] >= 0)[0]; k = np.nonzero(np.diff(xs) > 1)[0]
        if len(k):
            cx = (xs[k[0]] + xs[k[0] + 1] + 1) // 2
    return (z if z >= 3 else 6), cx


def step(g, side, k, bob):
    """正面／背面站姿的一步：把一隻腳抬高 k 格，身體下沉 bob 格。"""
    h, w = g.shape; z, cx = legzone(g); k = min(k, z - 2); top = h - z
    legs = g[top:].copy()
    if side and k > 0:
        cols = slice(0, cx) if side == 'L' else slice(cx, w)
        part = legs[:, cols].copy(); new = np.full_like(part, -1); new[:z - k] = part[k:]; legs[:, cols] = new
    o = np.full((h, w), -1, g.dtype); o[top:] = legs
    up = g[:top]; b = max(0, bob)
    dst = o[b:b + top]; m = up >= 0; dst[m] = up[m]
    return o


def mirror(fr, AX):
    """以錨點 x 為軸左右鏡射。"""
    FW = fr.shape[1]
    out = np.full_like(fr, -1)
    xs = 2 * AX - 1 - np.arange(FW)
    ok = (xs >= 0) & (xs < FW)
    out[:, xs[ok]] = fr[:, ok]
    if (fr[:, ~ok] >= 0).any():
        print('!! 鏡射後有格子超出畫格，被裁掉了（錨點不在畫格中央，請加大 frame）')
    return out


PREVIEW = r'''<!doctype html>
<html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAME__ 精靈圖預覽</title>
<style>
:root{--bg:#2a2834;--fg:#ece8e0;--card:#353241;--line:#4a4658}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif}
h1{font-size:18px;margin:0 0 4px}.sub{opacity:.7;margin-bottom:12px}
.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-bottom:16px}
.bar label{display:flex;gap:6px;align-items:center}
select,button{font:inherit;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 8px}
.grid{display:flex;flex-wrap:wrap;gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}
.card h2{font-size:13px;margin:0 0 6px;font-weight:600}.card small{opacity:.65;font-weight:400}
canvas{image-rendering:pixelated;display:block;max-width:100%}
body.light{--bg:#ece8e0;--fg:#2a2834;--card:#fff;--line:#cfc9bd}
body.checker canvas{background:repeating-conic-gradient(#8884 0 25%,#0000 0 50%) 0 0/16px 16px}
</style>
<h1>__NAME__</h1>
<div class="sub" id="sub"></div>
<div class="bar">
 <label>放大<select id="scale"><option>1<option>2<option selected>3<option>4<option>6<option>8</select></label>
 <label>速度<select id="speed"><option value="0.5">0.5×<option value="1" selected>1×<option value="2">2×</select></label>
 <label>背景<select id="bgsel"><option value="">深色<option value="light">淺色<option value="checker">格子</select></label>
 <button id="pause">暫停</button>
</div>
<div class="grid" id="grid"></div>
<script>
const DATA = __JSON__;
const img = new Image(); img.src = "__SHEET__";
const [FW, FH] = DATA.meta.frame_size, grid = document.getElementById('grid');
let scale = 3, speed = 1, paused = false, cards = [];
document.getElementById('sub').textContent =
  `畫格 ${FW}×${FH}，錨點 [${DATA.meta.anchor}]，色盤 ${DATA.meta.palette.length} 色，${Object.keys(DATA.frames).length} 格。放大一律是整數倍、最近鄰。`;
function build() {
  grid.innerHTML = ''; cards = [];
  for (const [name, a] of Object.entries(DATA.animations)) {
    const still = !a.frame_ms, n = still ? a.frames.length : 1;
    const c = document.createElement('canvas'); c.width = FW * n * scale; c.height = FH * scale;
    const d = document.createElement('div'); d.className = 'card';
    d.innerHTML = `<h2>${name} <small>${still ? a.frames.length + ' 張姿勢' : a.frames.length + ' 格 · ' + a.frame_ms + ' ms' + (a.loop ? '' : ' · 不循環')}</small></h2>`;
    d.appendChild(c); grid.appendChild(d);
    const ctx = c.getContext('2d'); ctx.imageSmoothingEnabled = false;
    cards.push({a, ctx, c, still, i: 0, t: 0});
  }
}
function draw(k) {
  const {a, ctx, c, still} = k; ctx.clearRect(0, 0, c.width, c.height);
  const list = still ? a.frames : [a.frames[k.i]];
  list.forEach((f, j) => { const r = DATA.frames[f]; ctx.drawImage(img, r.x, r.y, r.w, r.h, j * FW * scale, 0, FW * scale, FH * scale); });
}
let last = performance.now();
function tick(now) {
  const dt = (now - last) * speed; last = now;
  for (const k of cards) {
    if (!k.still && !paused) { k.t += dt; while (k.t >= k.a.frame_ms) { k.t -= k.a.frame_ms; k.i = (k.i + 1) % k.a.frames.length; if (!k.a.loop && k.i === 0) k.i = k.a.frames.length - 1; } }
    draw(k);
  }
  requestAnimationFrame(tick);
}
document.getElementById('scale').onchange = e => { scale = +e.target.value; build(); };
document.getElementById('speed').onchange = e => { speed = +e.target.value; };
document.getElementById('bgsel').onchange = e => { document.body.className = e.target.value; };
document.getElementById('pause').onclick = e => { paused = !paused; e.target.textContent = paused ? '播放' : '暫停'; };
img.onload = () => { build(); requestAnimationFrame(tick); };
</script></html>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True, help='角色設定檔（JSON），用裡面的 animations 清單')
    ap.add_argument('--frames', required=True, help='redraw_sheet.py 的輸出資料夾')
    ap.add_argument('--out', required=True, help='輸出資料夾')
    ap.add_argument('--name', help='檔名前綴（預設用設定檔的 name）')
    ap.add_argument('--gif-scale', type=int, default=4, help='GIF 的放大倍數（整數，預設 4）')
    ap.add_argument('--gif-bg', default='#2a2834', help='GIF 的背景色（預設 #2a2834）')
    a = ap.parse_args()

    cfg = px.load_config(a.config)
    name = a.name or cfg.get('name') or 'character'
    src = np.load(os.path.join(a.frames, f'{name}_grids.npz'))
    fj = json.load(open(os.path.join(a.frames, f'{name}_frames.json'), encoding='utf-8'))
    P = src['P']; S = {k[2:]: src[k] for k in src.files if k.startswith('f:')}
    FW, FH = fj['meta']['frame_size']; AX, BASE = fj['meta']['anchor']
    sheet_cfg = cfg.get('sheet', {})
    anims_cfg = cfg.get('animations') or [
        {'name': s['name'], 'section': s['name'], 'frame_ms': s.get('frame_ms', 0)} for s in sheet_cfg.get('sections', [])]

    F = {}; anims = {}; rows = []

    def need(n):
        if n not in S:
            raise SystemExit(f'animations 用了不存在的畫格 {n!r}。可用的畫格：{", ".join(S)}')
        return S[n]

    for ac in anims_cfg:
        an = ac['name']; ms = int(ac.get('frame_ms', 0)); imgs = []; srcn = []
        if 'mirror' in ac:
            ref = anims.get(ac['mirror']) or sys.exit(f"{an}：mirror 指到的動作 {ac['mirror']!r} 要寫在它前面")
            imgs = [mirror(F[k], AX) for k in ref['frames']]
            ms = int(ac.get('frame_ms', ref['frame_ms'])); srcn = [None] * len(imgs)
        elif 'step' in ac:
            st = ac['step']; base = crop(need(st['base']))
            for sd, k, bob in CYCLES[st.get('cycle', 'walk')]:
                if st.get('swap_sides') and sd:
                    sd = 'R' if sd == 'L' else 'L'
                imgs.append(place(step(base, sd, k, bob), FW, FH, AX, BASE, lift=-min(0, bob))[0]); srcn.append(None)
        else:
            srcn = list(ac['frames']) if 'frames' in ac else list(fj['sections'].get(ac.get('section'), []))
            if not srcn:
                raise SystemExit(f'{an}：要有 frames、section、mirror 或 step 其中一種')
            imgs = [need(n) for n in srcn]
        if ms > 0:
            keys = [f'{an}_{i}' for i in range(len(imgs))]
        elif len(imgs) == 1:
            keys = [an]
        else:
            keys = [n if n and n not in F else f'{an}_{n or i}' for i, n in enumerate(srcn)]
        for k, im in zip(keys, imgs):
            if k in F:
                raise SystemExit(f'畫格名稱重複：{k}（動作 {an}）')
            F[k] = im
        anims[an] = {'frames': keys, 'frame_ms': ms, 'loop': bool(ac.get('loop', ms > 0))}
        rows.append(keys)

    cols = sheet_cfg.get('columns') or max(len(r) for r in rows)
    info = {}; r = 0
    for keys in rows:
        for i, k in enumerate(keys):
            info[k] = {'x': (i % cols) * FW, 'y': (r + i // cols) * FH, 'w': FW, 'h': FH}
        r += max(1, math.ceil(len(keys) / cols))
    sheet = np.zeros((FH * r, FW * cols, 4), np.uint8)
    os.makedirs(os.path.join(a.out, 'frames'), exist_ok=True)
    os.makedirs(os.path.join(a.out, 'gif'), exist_ok=True)
    for k, fr in F.items():
        rgba = px.grid_rgba(fr, P); i = info[k]
        sheet[i['y']:i['y'] + FH, i['x']:i['x'] + FW] = rgba
        Image.fromarray(rgba).save(os.path.join(a.out, 'frames', k + '.png'))
    P_ = lambda f: px.out_path(a.out, f'{name}_{f}')
    px.save_scaled(sheet, P_('sheet.png'))
    px.save_scaled(sheet, P_('sheet_4x.png'), 4)
    meta = dict(fj['meta']); meta['image'] = f'{name}_sheet.png'
    meta['notes'] = '向左的畫格是向右的鏡射；用 step 產生的方向是由站姿抬腳加身體起伏做出的簡化版。frame_ms 為 0 的列是單張姿勢。'
    data = {'meta': meta, 'frames': info, 'animations': anims}
    json.dump(data, open(P_('sheet.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    # GIF：直接用色盤編號存，顏色和圖表完全相同
    bg = px.hex2rgb(a.gif_bg)
    pal = [*bg] + [int(v) for c in np.clip(np.round(P), 0, 255) for v in c]
    if len(P) > 255:
        print('!! 色盤超過 255 色，GIF 略過')
    else:
        for an, d in anims.items():
            if d['frame_ms'] <= 0 or len(d['frames']) < 2:
                continue
            ims = []
            for k in d['frames']:
                im = Image.fromarray((F[k] + 1).astype(np.uint8), 'P'); im.putpalette(pal)
                ims.append(im.resize((FW * a.gif_scale, FH * a.gif_scale), Image.NEAREST))
            ims[0].save(os.path.join(a.out, 'gif', an + '.gif'), save_all=True, append_images=ims[1:],
                        duration=d['frame_ms'], loop=0 if d['loop'] else 1, disposal=1)

    buf = io.BytesIO(); Image.fromarray(sheet).save(buf, 'PNG')
    html = (PREVIEW.replace('__NAME__', name).replace('__JSON__', json.dumps(data, ensure_ascii=False))
            .replace('__SHEET__', 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()))
    open(P_('preview.html'), 'w', encoding='utf-8').write(html)
    n_anim = sum(1 for d in anims.values() if d['frame_ms'] > 0)
    print(f'{name}：{len(F)} 個畫格、{len(anims)} 列（其中 {n_anim} 個動畫）→ {P_("sheet.png")}')
    print(f'預覽頁：{P_("preview.html")}')


if __name__ == '__main__':
    main()
