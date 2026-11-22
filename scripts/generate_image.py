#!/usr/bin/env python3
"""第 2、3 步（選用）：呼叫影像模型的 API 生成一張圖。每執行一次就是一次付費呼叫、產生一張圖。

  python generate_image.py --provider openai --prompt-file work/portrait_prompt.txt --out source/hero_portrait.png --size 1024x1024 --confirm-paid
  python generate_image.py --provider gemini --prompt-file work/sheet_prompt.txt --ref work/hero_scale_ref.png \
      --out source/hero_sheet_stand.png --aspect 16:9 --image-size 4K --confirm-paid

這個腳本是選用的。沒有 API 金鑰的人可以在 ChatGPT 或 Gemini 的網頁上用同一份提示詞（和參考圖）手動生成，
再把圖存到設定檔指定的來源路徑，後面的步驟完全一樣。

金鑰只從環境變數讀，不會寫進任何檔案，也不會印出來：
  --provider openai  讀 OPENAI_API_KEY（模型預設 gpt-image-1，可用 --model 或環境變數 OPENAI_IMAGE_MODEL 換）
  --provider gemini  讀 GEMINI_API_KEY 或 GOOGLE_API_KEY（模型預設 gemini-3-pro-image，可用 --model 或 GEMINI_IMAGE_MODEL 換）
模型名稱會隨時間改變，呼叫失敗時請查該服務目前的影像模型名稱。

計費：API 是照用量另外計費的，和 ChatGPT Plus／Pro、Gemini 的訂閱分開；有訂閱不代表 API 可以免費用。

安全設計：
  - 沒有加 --confirm-paid 時只會印出將要做的事，不會呼叫 API。請先讓使用者知道要生成幾張、用哪個模型，同意後才加。
  - 輸出檔已存在時會中止，不會覆寫，也不會自動重做。要重做請換檔名。
  - 只在 429／5xx 時重試（最多 2 次）；模型沒有回傳圖片時直接結束，不自動重試。
只用 Python 標準函式庫，不需要另外安裝套件。
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid


def post(url, headers, body, retries=2, timeout=600):
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, method='POST', headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:800]
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(10 * (attempt + 1)); continue
            sys.exit(f'API 錯誤 HTTP {e.code}：{msg}')
        except (urllib.error.URLError, TimeoutError) as e:
            sys.exit(f'連線失敗（沒有自動重試，請先確認這次有沒有被計費）：{e}')


def multipart(fields, files):
    b = uuid.uuid4().hex; out = []
    for k, v in fields.items():
        out.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, path in files:
        mime = mimetypes.guess_type(path)[0] or 'image/png'
        out.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{os.path.basename(path)}"\r\n'
                   f'Content-Type: {mime}\r\n\r\n'.encode() + open(path, 'rb').read() + b'\r\n')
    out.append(f'--{b}--\r\n'.encode())
    return b''.join(out), f'multipart/form-data; boundary={b}'


def openai(a, prompt, key):
    model = a.model or os.environ.get('OPENAI_IMAGE_MODEL') or 'gpt-image-1'
    auth = {'Authorization': f'Bearer {key}'}
    if a.ref:
        body, ctype = multipart({'model': model, 'prompt': prompt, 'size': a.size, 'n': '1'}, [('image[]', r) for r in a.ref])
        resp = post('https://api.openai.com/v1/images/edits', {**auth, 'Content-Type': ctype}, body)
    else:
        body = json.dumps({'model': model, 'prompt': prompt, 'size': a.size, 'n': 1}).encode()
        resp = post('https://api.openai.com/v1/images/generations', {**auth, 'Content-Type': 'application/json'}, body)
    d = (resp.get('data') or [{}])[0]
    if d.get('b64_json'):
        return base64.b64decode(d['b64_json']), 'image/png'
    if d.get('url'):
        with urllib.request.urlopen(d['url'], timeout=300) as r:
            return r.read(), r.headers.get('Content-Type', 'image/png')
    sys.exit('沒有回傳圖片：' + json.dumps(resp)[:600])


def gemini(a, prompt, key):
    model = a.model or os.environ.get('GEMINI_IMAGE_MODEL') or 'gemini-3-pro-image'
    parts = []
    for r in a.ref:
        mime = mimetypes.guess_type(r)[0] or 'image/png'
        parts.append({'inline_data': {'mime_type': mime, 'data': base64.b64encode(open(r, 'rb').read()).decode()}})
    parts.append({'text': prompt})
    cfg = {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': a.aspect}}
    if a.image_size:
        cfg['imageConfig']['imageSize'] = a.image_size
    body = json.dumps({'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': cfg}).encode()
    resp = post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                {'x-goog-api-key': key, 'Content-Type': 'application/json'}, body)
    for p in (resp.get('candidates') or [{}])[0].get('content', {}).get('parts', []):
        d = p.get('inline_data') or p.get('inlineData')
        if d:
            return base64.b64decode(d['data']), d.get('mime_type') or d.get('mimeType') or 'image/png'
    sys.exit('沒有回傳圖片：' + json.dumps(resp)[:600])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--provider', required=True, choices=['openai', 'gemini'])
    ap.add_argument('--prompt-file', required=True, help='提示詞的文字檔')
    ap.add_argument('--ref', action='append', default=[], help='參考圖，可以給多張（依序是 image 1、image 2…）')
    ap.add_argument('--out', required=True, help='輸出圖檔的路徑（副檔名會依回傳的格式調整）')
    ap.add_argument('--model', help='模型名稱（不給就用預設值或環境變數）')
    ap.add_argument('--size', default='1024x1024', help='openai：圖的尺寸，例如 1024x1024、1536x1024')
    ap.add_argument('--aspect', default='1:1', help='gemini：長寬比，例如 1:1、16:9')
    ap.add_argument('--image-size', help='gemini：解析度等級，例如 2K、4K（模型支援時才給）')
    ap.add_argument('--confirm-paid', action='store_true', help='使用者已經同意這次付費呼叫')
    a = ap.parse_args()

    prompt = open(a.prompt_file, encoding='utf-8').read().strip()
    stem = os.path.splitext(a.out)[0]
    exists = [stem + e for e in ('.png', '.jpg', '.jpeg', '.webp') if os.path.exists(stem + e)]
    if exists:
        sys.exit(f'輸出檔已存在：{exists[0]}。不會覆寫也不會自動重做；確定要再生成一張的話請換一個檔名。')
    for r in a.ref:
        if not os.path.exists(r):
            sys.exit(f'找不到參考圖：{r}')
    env = {'openai': ['OPENAI_API_KEY'], 'gemini': ['GEMINI_API_KEY', 'GOOGLE_API_KEY']}[a.provider]
    key = next((os.environ[e] for e in env if os.environ.get(e)), None)
    model = a.model or {'openai': os.environ.get('OPENAI_IMAGE_MODEL') or 'gpt-image-1',
                        'gemini': os.environ.get('GEMINI_IMAGE_MODEL') or 'gemini-3-pro-image'}[a.provider]
    print(f'將呼叫 {a.provider} 的付費 API 1 次（模型 {model}），生成 1 張圖 → {stem}.*，參考圖 {len(a.ref)} 張')
    if not key:
        sys.exit(f'沒有設定環境變數 {" 或 ".join(env)}。沒有金鑰也可以在 ChatGPT 或 Gemini 網頁用同一份提示詞手動生成，'
                 '再把圖存到上面的路徑。')
    if not a.confirm_paid:
        sys.exit('還沒有呼叫 API。請先讓使用者確認張數和模型，同意後加上 --confirm-paid 再執行。')

    t = time.time()
    data, mime = (openai if a.provider == 'openai' else gemini)(a, prompt, key)
    ext = '.jpg' if 'jpeg' in mime or 'jpg' in mime else '.webp' if 'webp' in mime else '.png'
    os.makedirs(os.path.dirname(os.path.abspath(stem)), exist_ok=True)
    with open(stem + ext, 'xb') as f:
        f.write(data)
    print(f'已生成 {stem + ext}（{len(data) / 1e6:.1f} MB，{time.time() - t:.0f} 秒）')


if __name__ == '__main__':
    main()
