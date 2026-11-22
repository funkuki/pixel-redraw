# 影像生成（第 2、3 步）

影像生成是選用的。這個 skill 的核心是第 4、5 步的重繪和動態；圖從哪裡來都可以，只要最後放在設定檔 `source` 指的位置。

## 兩種方式

### 手動：在網頁生成

不需要 API 金鑰，用 ChatGPT、Gemini 或其他有影像生成的服務都可以。

1. 把寫好的提示詞（`work/*_prompt.txt` 的內容）交給使用者。
2. 第 2 步要一起上傳風格參照圖（`assets/ref_chibi_flat.png` 或 `assets/ref_outline_street.png`，把完整路徑告訴使用者）；沒有參照圖，生成的樣子會和選定的風格差很遠。
3. 第 3 步要一起上傳參考圖：先 `make_scale_ref.py` 做出的比例參考圖，再來是已經確認過的圖表（有的話）。順序要和提示詞裡的 image 1、image 2 一致。
4. 請使用者下載**原始解析度**的圖（不要截圖，截圖會被縮放，格子就不整齊了），存到設定檔 `portrait.source` 或 `sheet.source` 的路徑。
5. 之後的步驟和 API 生成完全一樣。

網頁版通常不能指定輸出尺寸。拿到圖之後看實際的寬高；第 3 步的圖表尺寸如果和當初 `make_scale_ref.py` 用的 `--canvas` 不同，格距會等比例改變，重繪時用 `"pitch": "auto"` 量實際的格距即可。

### API：`scripts/generate_image.py`

```bash
python scripts/generate_image.py --provider openai --prompt-file work/portrait_prompt.txt \
    --ref <skill 資料夾>/assets/ref_chibi_flat.png \
    --out source/NAME_portrait.png --size 1024x1024 --confirm-paid

python scripts/generate_image.py --provider gemini --prompt-file work/sheet_stand_prompt.txt \
    --ref work/NAME_scale_ref.png --out source/NAME_sheet_stand.png --aspect 16:9 --image-size 4K --confirm-paid
```

- 執行一次就是一次付費呼叫、一張圖。
- `--ref` 可以給多張，順序就是提示詞裡的 image 1、image 2。
- 模型用 `--model` 指定，或設環境變數 `OPENAI_IMAGE_MODEL`、`GEMINI_IMAGE_MODEL`。腳本裡的預設模型名稱可能已經過時，呼叫失敗（HTTP 404、找不到模型）時查該服務目前的影像模型名稱再指定。
- 要接別家的模型，照 `generate_image.py` 裡 `openai()`、`gemini()` 的樣子加一個函式即可：輸入提示詞和參考圖，回傳圖檔的位元組。

## 金鑰

- 只從環境變數讀：`OPENAI_API_KEY`，或 `GEMINI_API_KEY`（也接受 `GOOGLE_API_KEY`）。
- 由使用者自己在終端機設定（例如寫在自己的 shell 設定檔裡）。不要請使用者把金鑰貼到對話裡，不要把金鑰寫進指令、設定檔或任何檔案，不要建立 `.env`。
- 確認有沒有設定時，只檢查變數存不存在，不要印出內容：

```bash
[ -n "$OPENAI_API_KEY" ] && echo 有設定 || echo 沒有設定
```

## 計費

- **API 和訂閱是分開計費的。** ChatGPT Plus／Pro 的訂閱只涵蓋在 ChatGPT 網頁和 App 裡使用；OpenAI API 要另外在 API 平台儲值，照用量扣款。Gemini 也一樣，Gemini 的訂閱方案和 Gemini API 的用量是兩筆帳。有訂閱不代表 API 可以免費用。
- 所以已經有訂閱的使用者，手動在網頁生成通常不用另外付錢；用 API 則每張圖都會扣款。使用者沒有特別要求自動化時，先建議手動。
- 每張圖的價格依模型和解析度不同，而且會調整。需要告訴使用者金額時，查該服務目前的價格頁，不要憑印象報價。

## 付費生成的規則

1. 呼叫 API 之前，先告訴使用者：這次要生成幾張（每張圖表是一次呼叫）、用哪個服務和模型、輸出的尺寸。得到明確同意才執行。
2. `--confirm-paid` 只在使用者同意之後才加。沒有這個旗標時腳本只會印出將要做的事。
3. 一次同意只涵蓋當時講好的張數。要多生成一張，就再問一次。
4. 結果不滿意時不要自動重做。回報哪裡有問題、建議怎麼改提示詞，由使用者決定要不要再生成。
5. 輸出檔已存在時腳本會中止，不會覆寫。要保留舊圖並再生成一張，就換一個檔名（例如 `_v2`）。
6. 連線逾時的時候，那次呼叫可能已經被計費。腳本不會自動重試，請告訴使用者這個情況，由他決定。

## 生成結果常見的問題

| 現象 | 處理 |
|---|---|
| 小人數量不對、被裁掉、互相黏住 | 這張圖表不能用。減少每張的小人數，或在提示詞加強留白的要求 |
| 臉被畫成別的風格 | 確認參考圖有用 `make_scale_ref.py` 處理過；加一張已確認的圖表當 image 2 |
| 像素比參考圖細或粗 | 提示詞寫明一個像素格是幾 px；還是不對就用 `"pitch": "auto"` 照實際的格距重繪，但小人大小會和預期不同 |
| 多了地板、陰影、文字、編號 | 少量可以在切圖時用 `box` 和 `min_pixels` 避開；黏在小人身上的要用 `fixes` 去掉或重新生成 |
| 走路每一格都一樣、或畫成跑步 | 提示詞逐格寫出腳的狀態；正面和背面的走路可以改用 `build_animation.py` 的 `step` 代替 |
