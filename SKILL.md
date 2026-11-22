---
name: pixel-redraw
description: 製作像素角色素材的完整流程：先用影像模型（ChatGPT、Gemini 等）生成像素風的角色立繪和精靈圖表，再用 Python 依網格重繪成真正的像素圖（一格一色、小色盤），最後排成動作、輸出精靈圖表、JSON、GIF 和可播放的預覽頁。使用者想做像素角色、pixel art sprite、sprite sheet、走路／跑步動畫，或手上有一張「看起來像像素圖但放大後格子不整齊」的 AI 圖想整理成乾淨的像素圖時使用，即使沒有提到這個 skill 的名字。
---

# 像素角色：AI 生成外觀，再依網格重繪

影像模型畫的「像素圖」不是真的像素圖：格子大小不一致、邊緣有漸層、同一塊顏色有幾十種相近色，放進遊戲或影片會糊。這個 skill 的做法是把 AI 圖只當成外觀的參考，用程式找出它的網格，每一格重新決定一個顏色，得到真正一格一像素的圖。

整個流程有五步。第 2、3、4 步做完都要**停下來把結果給使用者看，確認後才往下**；後面的步驟都建立在前一步上，前面沒確認就往下做，錯了要整批重來，付費生成的圖也白花了。

| 步驟 | 做什麼 | 產出 | 檢查點 |
|---|---|---|---|
| 1 想法 | 問清楚風格、角色設定、要哪些動作 | 設定檔草稿、提示詞 | |
| 2 生成角色圖 | 影像模型生成正面站姿的立繪 | AI 原圖 | 停，給使用者看 |
| 3 生成精靈圖表 | 拿立繪當參考，生成固定版面的圖表 | AI 圖表 | 停，給使用者看 |
| 4 重新繪製 | 立繪和圖表都依網格重繪 | `_1x.png`、`_10x.png`、畫格、JSON | 停，給使用者看 |
| 5 建立動態 | 排成動作、設定速度、鏡射 | 精靈圖表、JSON、GIF、預覽頁 | |

使用者手上已經有 AI 圖的話，從第 4 步開始；只有立繪就從第 3 步開始。把角色放進場景、做成影片或遊戲是之後的階段，不在這個 skill 裡。

## 像素規則

這幾條在每一步都適用。違反任何一條，成品看起來就不像像素圖。

- **一格一色**：不要漸層、抗鋸齒、半透明邊緣。
- **只用最近鄰、整數倍放大**：Pillow 用 `Image.NEAREST`，CSS 用 `image-rendering: pixelated`。非整數倍會讓格子有大有小。
- **同一個畫面只有一種像素比例**：角色、場景、特效的像素要一樣大。鏡頭放大要整個畫面一起放。
- **不用 upscaler**：Scale2x、xBR、AI 放大只會把邊緣修圓、破壞網格，不會增加細節。需要更清楚的角色，要用更多格子重新畫。
- **新圖沿用既有色盤**：同一位角色的新圖用她已有的顏色（設定檔的 `palette_from`），不另外取色。
- **做完放大 4–10 倍和原圖並排檢查**：自動結果在眼睛、眼鏡、手、腳最常出錯。用 Read 工具實際打開圖看，不要只看腳本印出的數字。

## 準備

腳本需要 Python 3 和 numpy、Pillow、scipy（`generate_image.py` 只用標準函式庫）。系統的 Python 通常沒有這些套件，先建虛擬環境：

```bash
python3 -m venv .venv && .venv/bin/pip install -r <skill 資料夾>/requirements.txt
```

每位角色一個工作資料夾，建議長這樣（路徑都可以改，寫在設定檔裡）：

```
my_character/
  character.json     設定檔（從 examples/character.example.json 複製來改）
  source/            AI 原圖（立繪、圖表）。只讀不改
  work/              提示詞、參考圖、檢查用的圖
  out/               成品
```

每張圖的手動設定（區塊範圍、小人名稱、要修正的格子、動作清單）都寫在 `character.json`，腳本本身不用改。格式見 [references/config.md](references/config.md)。

所有腳本的輸出位置都由 `--out` 指定，只會寫入自己的那幾個檔案，不會刪除資料夾。不要把 `--out` 指到放原圖的資料夾。

## 第 1 步：想法

向使用者問清楚這三件事，問到能寫出提示詞為止：

- **風格**：有兩種預設風格可以直接選，**色塊 Q 版**（大頭、無輪廓線、立繪約 90 格高）和**輪廓街拍**（比例較寫實、深色輪廓線、約 115 格高）。問之前先把兩張圖解給使用者看（`assets/style_chibi_flat.png`、`assets/style_outline_street.png`），用這兩個名稱來問；不要用「和某某作品同一路線」這種要先認識別的作品才聽得懂的說法。每種風格的格數、畫格、背景色、圖表尺寸和提示詞寫法在 [references/styles.md](references/styles.md)。使用者要別的風格時，把頭身比、有沒有輪廓線、配色氣氛、參考作品問清楚。
- **角色設定**：髮型髮色、服裝、配件、手上拿的東西。
- **要哪些動作**：轉身（幾個方向）、走路、跑步、哪些動作、哪些表情。

接著決定角色的解析度，這會決定後面所有的數字：

- 立繪：角色約 90–120 格高時臉和配件畫得出細節。
- 圖表裡的小人：受限於圖表尺寸。小人在圖上至少要 3 px 一格，低於這個數字模型畫不出乾淨的格子。圖表越大、每張的小人越少，每個小人能用的格子越多。動作多就分成多張圖表（例如站姿、側面走路、正面走路、動作各一張，每張 2 列 × 6 格）。

把決定寫進 `character.json` 草稿，並寫好提示詞（範本在 [references/prompts.md](references/prompts.md)）。

## 第 2 步：生成角色圖

用影像模型生成一張正面站姿、全身的像素風立繪，背景用單一純色。

- **一定要附風格參照圖**：只給文字提示詞，模型畫出來的比例、眼睛和格子大小會跑掉，和選定的風格差很遠。兩種預設風格的參照圖是 `assets/ref_chibi_flat.png` 和 `assets/ref_outline_street.png`；手動生成時把檔案位置告訴使用者、請他和提示詞一起上傳，API 生成時用 `--ref`。提示詞要寫明參照圖只用來定風格、比例和像素大小，不照抄角色（範本見 [references/prompts.md](references/prompts.md)）。使用者有自己的參照圖時用他的。

- 背景色不要出現在角色身上：角色有黑色輪廓就不要用黑底，穿白衣服就不要用白底，否則去背時會連輪廓或衣服一起去掉。
- 生成方式有兩種，結果一樣，由使用者選（細節見 [references/image_generation.md](references/image_generation.md)）：
  - **手動**：把提示詞交給使用者，請他在 ChatGPT 或 Gemini 的網頁生成，下載後存到設定檔的 `portrait.source`。不需要任何金鑰。
  - **API**：`scripts/generate_image.py`，金鑰只從環境變數讀（`OPENAI_API_KEY`、`GEMINI_API_KEY`）。
- **呼叫付費 API 之前，先告訴使用者這次要生成幾張、用哪個模型，得到同意才執行。** 腳本沒有 `--confirm-paid` 不會真的呼叫；這個旗標只在使用者同意之後才加。結果不滿意時不要自動重做，回報問題後由使用者決定要不要再生成（那是另一次付費）。
- API 是照用量另外計費的，和 ChatGPT、Gemini 的訂閱分開；使用者問起時要講清楚。
- 不要把金鑰寫進任何檔案或指令，也不要建立 `.env`。

**檢查點**：用 Read 打開生成的圖，給使用者看，確認外觀和比例是他要的。這時候改最便宜。

## 第 3 步：生成精靈圖表

拿立繪當參考，生成轉身、走路、跑步、動作、表情的圖表。這一步有兩個重點。

**參考圖要先處理。** 直接給模型放大的立繪，它會照立繪的像素大小畫，圖表塞不下、格距對不上，臉也容易被改畫。要給的是「和圖表同尺寸的白底畫布，上面放著縮到圖表格距的立繪」，模型才會照這個大小和像素比例畫每個小人。所以最好先做完第 4 步的立繪重繪，再回來做這一步：

```bash
python scripts/make_scale_ref.py --portrait out/NAME_1x.png --canvas 5504x3072 --rows 2 --cols 6 --out work/NAME_scale_ref.png
```

腳本會印出格距、建議的畫格大小和錨點，把它們記到設定檔的 `sheet` 區段和提示詞裡。如果它說格距太小，就加大圖表尺寸或減少每張的小人數。

**提示詞要固定版面。** 寫明幾列、每列幾格、每一列是什麼動作、每一格是什麼姿勢，小人之間留白、不互相碰到，背景純白，不要地板、陰影、文字、編號、格線。版面固定了，第 4 步才能照「第幾列第幾個」自動切圖和命名。範本在 [references/prompts.md](references/prompts.md)。

已經有一張滿意的圖表之後，生成下一張時把它當第二張參考圖（像素大小、小人大小、輪廓畫法照它），各張之間會一致得多。

生成方式和付費規則同第 2 步：先報張數（有幾張圖表就是幾次呼叫），同意後才執行，不自動重做。

**檢查點**：打開每張圖表給使用者看。要看的是：小人數量和順序對不對、有沒有被裁掉或互相黏住、臉有沒有被改畫、走路的腳有沒有交替。有問題的圖表在這裡就決定重做或放棄，不要帶進第 4 步。

## 第 4 步：重新繪製

### 立繪

```bash
python scripts/redraw_portrait.py --config character.json --out out/
```

流程是找網格 → 取色盤 → 一格一色 → 清雜點 → 去背 → 人工修正。跑完依序看三張圖：

1. `NAME_grid_check.png`：青色格線要貼著每個像素的邊。**自動找到的格距常常是實際的兩倍或一半**（一格裡看得到 2×2 個小色塊就是大了一倍）。不對就在設定檔的 `portrait` 加 `"pitch_hint"`（大概的格距，等於圖寬 ÷ 目測的格數）重跑。AI 圖的 x、y 格距可能不一樣，這是正常的。
2. `NAME_compare.png`：原圖和重繪並排。確認整體形狀、顏色沒有跑掉。
3. 眼睛、手、腳：用 `scripts/compare.py` 的 `--box` 放大局部和原圖並排。

**人工修正。** 眼睛幾乎每次都要修：AI 圖的眼睛高光和輪廓跨在格線上，自動結果會歪或不對稱。做法是指定格子重畫：

```bash
python scripts/inspect_cells.py out/NAME_data.npz --box 45 40 85 60 --png work/eyes.png
```

它會把那個範圍印成文字圖樣（每個字元是一個色盤編號），並輸出附座標的放大圖。照著原圖決定每一格該是什麼顏色，寫成設定檔 `portrait.fixes` 裡的 pattern（格式見 [references/config.md](references/config.md)），再用 `--reuse` 重跑（跳過找網格，只重套去背和修正）。修正只用色盤裡已有的顏色。每修一次都放大對照原圖，直到兩隻眼睛對稱、手指和鞋子的形狀合理。

### 精靈圖表

```bash
python scripts/redraw_sheet.py --config character.json --out out/ --extract-only   # 先確認切圖
python scripts/redraw_sheet.py --config character.json --out out/
```

先用 `--extract-only` 看 `NAME_extract_check.png`：每個小人要有一個綠框，名稱要對。切錯的常見原因和調法（`box`、`min_pixels`、`bg_tolerance`）見 [references/config.md](references/config.md)。

切對之後跑完整流程：決定每個區塊的格距（把角色高度統一成 `height_cells`）→ 逐個小人搜尋格線起點並取樣 → 所有小人共用一份色盤 → 排進固定畫格、頭部中心和腳底對齊錨點。設定 `palette_from` 指到立繪的 `NAME_data.npz`，圖表的顏色就會對到立繪的色盤。

看 `NAME_frames_4x.png`，逐格檢查：

- 眼睛、手、腳有沒有壞掉。
- 兩腿之間、手臂和身體之間有沒有殘留的背景色（白底圖表最常見）。
- 輪廓外側有沒有零星的灰白格子（取樣點落在輪廓和背景交界的殘影）。
- 同一個動畫的各格，頭的大小和位置有沒有跳動。

修法一樣是指定格子，寫在 `sheet.fixes` 裡該畫格的名稱下面，座標是畫格內的格子（`inspect_cells.py out/NAME_grids.npz --frame 畫格名稱`），再用 `--reuse` 重跑。

**檢查點**：把立繪的 `_10x.png` 和 `NAME_frames_4x.png` 給使用者看，說明修了哪些地方、還有哪些地方不理想。

## 第 5 步：建立動態

```bash
python scripts/build_animation.py --config character.json --frames out/ --out out/
```

設定檔的 `animations` 清單決定每一列是什麼：哪些畫格、每格幾毫秒、要不要循環。向左的動作用 `mirror` 從向右鏡射。沒有正面或背面走路的參考圖時，可以用 `step` 從站姿做出簡化的踏步（抬腳加身體起伏），效果不如重繪的畫格自然，只當替代方案。

走路一般每格 100–125 毫秒，跑步 80–100 毫秒，轉身展示 400 毫秒。先照這個設，看了預覽再調。

輸出：`NAME_sheet.png`（另有 4 倍放大版）、`NAME_sheet.json`（畫格位置、動作、速度、錨點、色盤）、`frames/`、`gif/`、`NAME_preview.html`。預覽頁是單一檔案，直接用瀏覽器打開就能播放每個動作，請使用者看動作順不順；GIF 的顏色和圖表完全相同，可以用 Read 打開檢查。

動作不順時，通常是某幾格的頭部位置跳動（回第 4 步用 `fixes` 修，或從 `animations` 裡拿掉那一格），或速度不對（改 `frame_ms`）。

## 交付時要告訴使用者的事

- 成品在哪裡、每個檔案是什麼。
- 錨點的意思：x 是頭部中心，y 是腳底的地面線；放進場景時把錨點對到站位。
- 哪些畫格是鏡射或 `step` 產生的。
- 做了哪些人工修正，還有哪些地方不理想。

## 參考文件

- [references/config.md](references/config.md)：設定檔每個欄位的意思、修正格式、切圖和格距的調法、常見問題。寫或改 `character.json` 時讀。
- [references/styles.md](references/styles.md)：兩種預設風格的圖解、規格和選法。第 1 步問風格之前讀。
- [references/prompts.md](references/prompts.md)：立繪和圖表的提示詞範本。第 1–3 步寫提示詞時讀。
- [references/image_generation.md](references/image_generation.md)：手動生成和 API 生成的做法、金鑰、計費。第 2、3 步讀。
- `examples/character.example.json`：完整的設定檔範例（深色底、各區塊大小不一的圖表，用 `box` 和 `scale` 逐區塊設定）。
- `examples/character.grid_layout.example.json`：照第 3 步生成的白底固定版面圖表（多張圖表、`row`、`"pitch": "auto"`）。
