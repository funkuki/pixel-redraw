"""像素角色流程的共用函式：設定檔、網格、色盤、指定格子修正、輸出。

需要 numpy、Pillow、scipy。所有路徑都由呼叫端用參數或設定檔指定。
"""
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


# ---------- 設定檔與路徑 ----------

def load_config(path):
    """讀角色設定檔（JSON）。設定檔裡的相對路徑以設定檔所在資料夾為準。"""
    with open(path, encoding='utf-8') as f:
        cfg = json.load(f)
    cfg['_dir'] = os.path.dirname(os.path.abspath(path))
    return cfg


def resolve(cfg, p):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(cfg['_dir'], p))


def out_path(out_dir, filename, sources=()):
    """回傳輸出路徑；輸出檔和來源檔是同一個檔案時中止，避免蓋掉原圖。"""
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, filename)
    for s in sources:
        if s and os.path.exists(s) and os.path.exists(p) and os.path.samefile(s, p):
            raise SystemExit(f'輸出檔會蓋掉來源圖：{p}。請換一個輸出資料夾。')
    return p


def load_rgb(path):
    return np.asarray(Image.open(path).convert('RGB')).astype(np.float32)


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(c):
    return '#%02x%02x%02x' % tuple(int(round(float(v))) for v in c[:3])


def background_color(a, spec='auto'):
    """背景色：'auto' 取四個邊緣像素的中位數，也可以給 '#rrggbb' 或 [r, g, b]。"""
    if spec in (None, 'auto'):
        edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
        return np.median(edge, 0)
    if isinstance(spec, str):
        return np.array(hex2rgb(spec), np.float32)
    return np.array(spec, np.float32)


# ---------- 網格 ----------

def edges(p, ph, n):
    """格距 p、起點 ph 的格線位置（整數像素），涵蓋 0..n。"""
    e = np.round(np.arange(ph - p * np.ceil(ph / p), n + p, p)).astype(int)
    return np.unique(np.clip(e, 0, n))


def grid_error(im, ex, ey):
    """每一格內的顏色變異總和（越小表示格線越貼合色塊）。"""
    H, W, _ = im.shape
    cs = np.add.reduceat(np.add.reduceat(im, ey[:-1], axis=0), ex[:-1], axis=1)
    cs2 = np.add.reduceat(np.add.reduceat(im ** 2, ey[:-1], axis=0), ex[:-1], axis=1)
    cnt = (np.diff(ey)[:, None] * np.diff(ex)[None, :])[..., None]
    return float((cs2 - cs ** 2 / cnt).sum() / (H * W))


def estimate_pitch(im, lo=3.0, hi=40.0, hint=None, log=None):
    """粗估格距，回傳 (x 格距, y 格距)，單位 px。

    把相鄰像素的色差投影到軸上，取頻譜最強的週期。AI 圖的 x、y 格距常常不一樣，所以兩軸分開估。
    注意：AI 圖常常同時在「一格」和「兩格」的週期上都有峰值，自動結果可能是實際格距的兩倍或一半，
    一定要看 grid_check 圖確認格線有沒有貼著像素。不對時給 hint（大概的格距，例如 圖寬 ÷ 目測的格數），
    會改取 hint ±12% 內最強的週期。
    """
    res = []
    for ax, label in ((1, 'x'), (0, 'y')):
        g = np.abs(np.diff(im, axis=ax)).sum(axis=(1 - ax, 2))
        g = g - g.mean()
        N = 1 << int(np.ceil(np.log2(len(g) * 8)))
        S = np.abs(np.fft.rfft(g * np.hanning(len(g)), N))
        f = np.arange(len(S)) / N
        f[0] = 1e-9
        ok = (f >= 1 / hi) & (f <= 1 / lo)
        pk = [i for i in np.nonzero(ok)[0][1:-1] if S[i] >= S[i - 1] and S[i] >= S[i + 1]]
        pk.sort(key=lambda i: -S[i])
        if log:
            log(f'  {label} 軸的候選格距（px：相對強度）：' + '、'.join(f'{1 / f[i]:.2f}：{S[i] / S[pk[0]]:.2f}' for i in pk[:5]))
        if hint:
            near = [i for i in pk if hint * 0.88 <= 1 / f[i] <= hint * 1.12]
            res.append(float(1 / f[near[0]]) if near else float(hint))
        else:
            res.append(float(1 / f[pk[0]]))
    return tuple(res)


def search_grid(im, lo, hi, step=0.01, phase_step=0.25, iters=3, log=None):
    """x、y 兩軸各自搜尋格距和起點，取格內變異最小的一組。回傳 (px, phx, py, phy, err)。"""
    H, W, _ = im.shape
    lo_x, hi_x = (lo, hi) if np.isscalar(lo) else ((lo[0], hi[0]))
    lo_y, hi_y = (lo, hi) if np.isscalar(lo) else ((lo[1], hi[1]))
    Rx = np.arange(lo_x, hi_x + 1e-9, step)
    Ry = np.arange(lo_y, hi_y + 1e-9, step)
    px, phx, py, phy = (lo_x + hi_x) / 2, 0.0, (lo_y + hi_y) / 2, 0.0
    b = None
    total = float((im ** 2).sum())

    def best(axis, fixed_edges, R, n):
        # 格內變異 = Σ像素² − Σ(格內總和²/格內像素數)。先沿固定的那一軸加總，候選格線只需要再加總另一軸。
        pre = np.add.reduceat(im, fixed_edges[:-1], axis=1 - axis)
        fc = np.diff(fixed_edges).astype(np.float64)
        out = None
        for p in R:
            for ph in np.arange(0, p, phase_step):
                e = edges(p, ph, n)
                cs = np.add.reduceat(pre, e[:-1], axis=axis).astype(np.float64)
                ec = np.diff(e).astype(np.float64)
                cnt = (fc[:, None] * ec[None, :]) if axis == 1 else (ec[:, None] * fc[None, :])
                v = (total - (cs ** 2 / cnt[..., None]).sum()) / (H * W)
                if out is None or v < out[0]:
                    out = (v, p, ph)
        return out

    for it in range(iters):
        b = best(1, edges(py, phy, H), Rx, W)
        px, phx = b[1], b[2]
        b = best(0, edges(px, phx, W), Ry, H)
        py, phy = b[1], b[2]
        if log:
            log(f'  第 {it + 1} 輪：x 格距 {px:.2f} 起點 {phx:.2f}，y 格距 {py:.2f} 起點 {phy:.2f}，變異 {b[0]:.1f}')
    return float(px), float(phx), float(py), float(phy), b[0]


# ---------- 色盤 ----------

def flat_palette(im, cell_area, flat_t=5, quant=6, merge_max=13, merge_dist=16,
                 min_seed_cells=0.70, min_cells=1.68):
    """從平坦區域取色盤：只看和上下左右差異很小的像素，量化後合併相近色，丟掉太少見的。"""
    ii = im.astype(np.int32)
    d = np.zeros(im.shape[:2])
    for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
        d = np.maximum(d, np.abs(ii - np.roll(ii, sh, axis=ax)).max(axis=2))
    flat = ii[d < flat_t]
    q = flat // quant
    keys, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    means = np.stack([np.bincount(inv, weights=flat[:, c]) / cnt for c in range(3)], 1)
    pal = []
    for k in np.argsort(-cnt):
        if cnt[k] < min_seed_cells * cell_area:
            break
        m = means[k]
        for p in pal:
            if np.abs(p[0] - m).max() < merge_max and np.linalg.norm(p[0] - m) < merge_dist:
                p[0] = (p[0] * p[1] + m * cnt[k]) / (p[1] + cnt[k]); p[1] += cnt[k]
                break
        else:
            pal.append([m.copy(), cnt[k]])
    return np.array([np.round(p[0]) for p in pal if p[1] >= min_cells * cell_area], np.float32)


def merged_palette(colors, quant=8, merge_max=17, merge_dist=22, min_count=10):
    """把一堆格子顏色（N×3）合併成色盤。用在同一位角色的所有小人共用一份色盤。"""
    q = (colors // quant).astype(int)
    keys, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    means = np.stack([np.bincount(inv, weights=colors[:, c]) / cnt for c in range(3)], 1)
    pal = []
    for k in np.argsort(-cnt):
        m = means[k]
        for p in pal:
            if np.abs(p[0] - m).max() < merge_max and np.linalg.norm(p[0] - m) < merge_dist:
                p[2] += cnt[k]
                break
        else:
            pal.append([m.copy(), cnt[k], cnt[k]])
    return np.array([np.round(p[0]) for p in pal if p[2] >= min_count], np.float32)


def snap_palette(P, base, dist=30):
    """把色盤 P 裡和既有色盤 base 夠接近的顏色換成 base 的顏色（新圖沿用既有色盤）。

    回傳 (新色盤, 舊編號→新編號的對照)。base 沒有的顏色保留並排在後面。
    """
    base = np.asarray(base, np.float32)
    out = [tuple(c) for c in base]
    remap = np.zeros(len(P), int)
    for i, c in enumerate(P):
        d = np.linalg.norm(base - c, axis=1)
        if d.min() <= dist:
            remap[i] = int(d.argmin())
        else:
            out.append(tuple(c)); remap[i] = len(out) - 1
    used = np.unique(remap)
    lut = {u: k for k, u in enumerate(used)}
    return np.array([out[u] for u in used], np.float32), np.array([lut[r] for r in remap])


def read_palette(path):
    """讀既有色盤：.npz（鍵 P）、.json（meta.palette 或 palette 的 hex 清單）、或一張 PNG（取不透明像素的顏色）。"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.npz':
        return np.asarray(np.load(path)['P'], np.float32)
    if ext == '.json':
        j = json.load(open(path, encoding='utf-8'))
        pal = j.get('palette') or j.get('meta', {}).get('palette')
        return np.array([hex2rgb(h) for h in pal], np.float32)
    a = np.asarray(Image.open(path).convert('RGBA'))
    return np.unique(a[a[..., 3] > 0][:, :3], axis=0).astype(np.float32)


# ---------- 指定格子的人工修正 ----------

def color_index(P, v, allow_new=False):
    """把設定檔裡的顏色（色盤編號、'#rrggbb'、None/-1 表示透明）換成色盤編號。回傳 (P, 編號)。"""
    if v is None or v == -1 or v == 'transparent':
        return P, -1
    if isinstance(v, int):
        if not 0 <= v < len(P):
            raise SystemExit(f'修正用的色盤編號 {v} 超出範圍（色盤有 {len(P)} 色）')
        return P, v
    c = np.array(hex2rgb(v), np.float32)
    d = np.linalg.norm(P - c, axis=1)
    if d.min() < 1.5:
        return P, int(d.argmin())
    if not allow_new:
        near = rgb2hex(P[d.argmin()])
        raise SystemExit(f'修正用的顏色 {v} 不在色盤裡（最接近的是 {near}）。'
                         '請改用色盤裡的顏色，或在該筆修正加上 "allow_new": true。')
    return np.concatenate([P, c[None]]), len(P)


def apply_fixes(g, P, fixes):
    """套用指定格子的修正。g 是色盤編號的二維陣列（-1 透明），座標是格子的 (欄 x, 列 y)。

    每筆修正是下列其中一種：
      {"legend": {"W": 7, "I": "#82477f", ".": null}, "rows": [45, 46], "col": 53, "pattern": "  cWWWWccc"}
          rows 裡的每一列都從第 col 欄開始照 pattern 畫，空白字元表示不改。
          rows 也可以寫成 [起, 迄] 搭配 "row_range": true。
      {"cells": [[x, y], ...], "color": 7}            把這些格子改成同一個顏色
      {"cells": [[x, y], ...], "copy_from": [x, y]}   顏色取自另一格
      {"flood": [x, y], "color": null}                從這格往外把相連的同色格子全部改掉（常用來挖掉被包住的背景）
    """
    g = g.copy()
    H, W = g.shape
    n = 0
    for f in fixes or []:
        new = bool(f.get('allow_new'))
        if 'pattern' in f:
            legend = {}
            for ch, v in f['legend'].items():
                P, legend[ch] = color_index(P, v, new)
            rows = f['rows']
            if f.get('row_range'):
                rows = range(rows[0], rows[1] + 1)
            for j in rows:
                for k, ch in enumerate(f['pattern']):
                    if ch == ' ':
                        continue
                    if ch not in legend:
                        raise SystemExit(f'pattern 用了 legend 沒有的字元 {ch!r}')
                    x = f['col'] + k
                    if 0 <= j < H and 0 <= x < W:
                        g[j, x] = legend[ch]; n += 1
        elif 'flood' in f:
            x, y = f['flood']
            P, ci = color_index(P, f.get('color'), new)
            lab, _ = ndi.label(g == g[y, x])
            m = lab == lab[y, x]
            g[m] = ci; n += int(m.sum())
        elif 'cells' in f:
            if 'copy_from' in f:
                sx, sy = f['copy_from']; ci = g[sy, sx]
            else:
                P, ci = color_index(P, f.get('color'), new)
            for x, y in f['cells']:
                g[y, x] = ci; n += 1
        else:
            raise SystemExit(f'看不懂的修正：{f}')
    return g, P, n


# ---------- 清雜點 ----------

def remove_specks(g, P, min_neighbors=4, max_dist=28):
    """周圍八格沒有同色、而且和鄰居多數色很接近的單格，換成多數色。"""
    before = g.copy(); out = g.copy()
    Pf = np.asarray(P, float)
    H, W = g.shape
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            c = before[y, x]
            if c < 0:
                continue
            nb = np.delete(before[y - 1:y + 2, x - 1:x + 2].ravel(), 4)
            if (nb == c).any():
                continue
            v = nb[nb >= 0]
            if len(v) < 5:
                continue
            u, cn = np.unique(v, return_counts=True)
            mj = u[np.argmax(cn)]
            if cn.max() >= min_neighbors and np.linalg.norm(Pf[mj] - Pf[c]) < max_dist:
                out[y, x] = mj
    return out


# ---------- 輸出 ----------

def grid_overlay(im, ex, ey, path, size=48):
    """把來源圖中央約 size 格的範圍放大，畫上格線，用來確認格線有沒有貼著像素。"""
    H, W, _ = im.shape
    cx, cy = len(ex) // 2, len(ey) // 2
    i0, i1 = max(0, cx - size // 2), min(len(ex) - 1, cx + size // 2)
    j0, j1 = max(0, cy - size // 2), min(len(ey) - 1, cy + size // 2)
    x0, x1, y0, y1 = ex[i0], ex[i1], ey[j0], ey[j1]
    k = max(2, int(round(1600 / max(1, x1 - x0))))
    crop = Image.fromarray(im[y0:y1, x0:x1].astype(np.uint8)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST)
    a = np.asarray(crop).copy()
    for x in ex[i0:i1 + 1]:
        a[:, min(a.shape[1] - 1, (x - x0) * k)] = (0, 255, 255)
    for y in ey[j0:j1 + 1]:
        a[min(a.shape[0] - 1, (y - y0) * k), :] = (0, 255, 255)
    Image.fromarray(a).save(path)


def grid_rgba(g, P):
    o = np.zeros(g.shape + (4,), np.uint8)
    m = g >= 0
    o[m, :3] = np.clip(np.round(np.asarray(P)[g[m]]), 0, 255).astype(np.uint8)
    o[m, 3] = 255
    return o


def save_scaled(arr, path, scale=1):
    """存 PNG；scale 只能是整數，一律最近鄰放大。"""
    im = arr if isinstance(arr, Image.Image) else Image.fromarray(arr)
    if scale != 1:
        assert int(scale) == scale and scale >= 1, '只用整數倍放大'
        im = im.resize((im.width * int(scale), im.height * int(scale)), Image.NEAREST)
    im.save(path)
    return im


def on_background(rgba, bg=(42, 40, 52)):
    b = Image.new('RGBA', (rgba.shape[1], rgba.shape[0]), tuple(bg) + (255,))
    b.alpha_composite(Image.fromarray(rgba))
    return b.convert('RGB')


def text_map(g, P, box=None):
    """把格子印成文字圖樣（每個色盤編號一個字元），方便寫 pattern 修正。"""
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*+=?<>'
    x0, y0, x1, y1 = box or (0, 0, g.shape[1], g.shape[0])
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(g.shape[1], x1), min(g.shape[0], y1)
    lines = ['     ' + ''.join(str((x // 10) % 10) if x % 10 == 0 else ' ' for x in range(x0, x1)),
             '     ' + ''.join(str(x % 10) for x in range(x0, x1))]
    used = set()
    for y in range(y0, y1):
        row = ''
        for x in range(x0, x1):
            v = int(g[y, x])
            row += '.' if v < 0 else chars[v % len(chars)]
            if v >= 0:
                used.add(v)
        lines.append(f'{y:4d} {row}')
    lines.append('')
    lines.append('色盤（字元 = 編號 顏色）：' + '  '.join(f'{chars[v % len(chars)]}={v} {rgb2hex(P[v])}' for v in sorted(used)))
    return '\n'.join(lines)
