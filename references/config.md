# 設定檔 `character.json`

每位角色一份 JSON。裡面的相對路徑以設定檔所在的資料夾為準。完整範例在 `examples/character.example.json`。

```json
{
  "name": "hero",
  "portrait": { ... },
  "sheet": { ... },
  "animations": [ ... ]
}
```

`name` 是所有輸出檔的檔名前綴。

## 目錄

- [portrait：立繪](#portrait立繪)
- [sheet：精靈圖表](#sheet精靈圖表)
- [fixes：指定格子的人工修正](#fixes指定格子的人工修正)
- [animations：動作](#animations動作)
- [常見問題](#常見問題)

## portrait：立繪

給 `redraw_portrait.py` 用。

| 欄位 | 意思 | 預設 |
|---|---|---|
| `source` | AI 原圖的路徑 | 必填 |
| `pitch_hint` | 大概的格距（px），等於圖寬 ÷ 目測的格數。自動結果是實際的兩倍或一半時用 | 自動 |
| `pitch_range` | 格距的搜尋範圍 `[最小, 最大]`；兩軸不同時寫 `[[x最小, y最小], [x最大, y最大]]` | 粗估值 ±5% |
| `pitch`、`origin` | 直接指定格距（數字或 `[x, y]`）和起點 `[x, y]`。網格很均勻的大圖用這個最快 | |
| `background` | 背景色：`"auto"`（取畫面邊緣）、`"#rrggbb"` 或 `[r, g, b]` | `"auto"` |
| `remove_background` | `"border"`：只去掉和畫面邊緣相連的背景色。`"all"`：背景色的格子全部去掉。`false`：不去背 | `"border"` |
| `holes` | `"border"` 模式下，被輪廓包住的背景，寫格座標 `[[x, y], ...]`，會從這些格子往外填成透明 | |
| `keep_largest` | `true` 時只留最大的一塊，丟掉飄在角色外面的零星格子 | `false` |
| `keep_ratio` | 清雜點時，孤立的單格在原圖裡佔到這個比例就視為真的細節而保留 | `0.7` |
| `fixes` | 指定格子的人工修正，見下面 | |

去背模式怎麼選：背景色完全沒有用在角色身上（例如黑底、角色沒有黑色）用 `"all"` 最乾淨。角色身上有和背景一樣的顏色（白底上的白襯衫、白襪）用 `"border"`，被包住的背景（兩腿之間、手臂和身體之間）再用 `holes` 指定。

格距的判斷：`pitch_hint`、`pitch_range`、`pitch` 三選一，都不寫就完全自動。跑完一定要看 `NAME_grid_check.png`。

## sheet：精靈圖表

給 `redraw_sheet.py` 用。

| 欄位 | 意思 | 預設 |
|---|---|---|
| `source` | AI 圖表的路徑。有多張圖表時，可以在每個區塊各自寫 `source` | 必填 |
| `background`、`bg_tolerance` | 背景色，以及和背景差多少（RGB 差的總和）才算前景 | `"auto"`、`70` |
| `frame` | 畫格大小 `[寬, 高]`（格）。要放得下最大的姿勢 | `[64, 64]` |
| `anchor` | 錨點 `[x, y]`：x 是頭部中心要對齊的欄，y 是腳底的地面線（腳底最下面一列是 y−1） | `[寬/2, 高−2]` |
| `height_cells` | 站姿的角色高度（格）。用 `"height"` 決定格距時，角色會被統一成這個高度 | `50` |
| `columns` | 輸出圖表每列幾格 | 最長的區塊 |
| `pitch` | 整張圖表共用的格距：數字，或 `"auto"`（自動量，可搭配 `pitch_hint`、`pitch_range`） | 各區塊用 `"height"` |
| `grid` | `{"rows": 2, "cols": 6}`：圖表是平均分割的版面時用，區塊就可以只寫 `row` | |
| `enclosed` | 被小人輪廓包住、顏色接近背景的區域：`"auto"` 只留和背景有一點差異的；`"keep"` 全部留下（白底圖表用這個，眼白和白衣服才不會破洞，兩腿之間的背景再用 `fixes` 的 flood 挖掉） | `"auto"` |
| `trim_fringe` | 去掉輪廓外側的殘影：貼著透明區、和背景色差（RGB 差的總和）小於這個值的格子。白底、有深色輪廓的圖表可以設 `150`–`200`；角色邊緣有淺色而且沒有輪廓時不要用 | `0`（不做） |
| `min_pixels` | 小於這個像素數的東西（動作線、說明文字）不算小人 | 圖面積的 0.16% |
| `palette_from` | 既有色盤：立繪的 `NAME_data.npz`、有 `palette` 的 JSON、或一張 `_1x.png` | |
| `palette_snap` | 和既有色盤的距離在這以內就直接用既有的顏色 | `30` |
| `remove_specks` | `true` 時清掉和周圍顏色很接近的孤立單格 | `false` |
| `sections` | 區塊清單，見下面 | 必填 |
| `fixes` | `{"畫格名稱": [修正, ...]}`，座標是畫格內的格子 | |

### sections：區塊

一個區塊是圖表上的一塊範圍，裡面的小人由左到右依序命名。每個區塊在輸出的 `NAME_frames.png` 佔一列。

| 欄位 | 意思 |
|---|---|
| `name` | 區塊名稱（`animations` 會用到） |
| `box` | 這個區塊在來源圖上的範圍 `[x0, y0, x1, y1]`（px）。要包住所有小人，並避開說明文字 |
| `row` | 代替 `box`：這個區塊是 `grid` 版面的第幾列（從 0 算），範圍是整列 |
| `names` | 每個小人的名稱，由左到右。全部區塊合起來不能重複 |
| `count` | 代替 `names`：有幾個小人，名稱自動取成 `區塊名_0`、`區塊名_1`… |
| `source` | 這個區塊用另一張圖表時寫 |
| `scale` | 這個區塊的格距怎麼決定，見下面 |
| `scale_sprite` | `"height"` 或被別人 `head_of` 參照時，只看這一個小人（例如只看正面站姿） |
| `align` | `"head"`：用小人上方 45% 的重心當頭部中心。`"center"`：用小人的中線（只有頭的表情區塊用這個） |
| `keep_lift` | `true` 時保留離地高度：這一列腳底最低的當地面，其他小人照來源圖上的高度差抬高（跑步的騰空格） |
| `frame_ms` | 沒有寫 `animations` 時，這個區塊當動畫的每格毫秒數 |

### scale：格距怎麼決定

AI 圖表裡每個區塊的小人大小常常不同，所以格距是逐區塊決定的，目標是讓所有畫格裡的角色一樣大。

- `"height"`：這個區塊是完整的站姿。格距 = 小人高度的中位數 ÷ `height_cells`。轉身、走路用這個。
- `{"head_of": "區塊名"}`：姿勢不是站直的（跑步前傾、坐下、蹲），高度不能拿來算，改成讓頭和另一個區塊一樣寬。只有頭或半身的區塊再加 `"head_frac": 1.0`。
- 數字：直接指定格距（px）。
- 沒寫就用 `sheet.pitch`。照第 3 步的做法生成的圖表（參考圖是固定格距）整張都是同一個格距，寫 `"pitch": "auto"` 或 `make_scale_ref.py` 印出的數字即可，不用逐區塊設。

用 `"pitch": "auto"` 時看腳本印出的候選格距，確認和 `make_scale_ref.py` 當初算的差不多；差很多表示模型沒有照參考圖的比例畫。

## fixes：指定格子的人工修正

`portrait.fixes` 是一個清單，座標是整張立繪的格子；`sheet.fixes` 是 `{"畫格名稱": 清單}`，座標是畫格內的格子。座標都是 `(欄 x, 列 y)`，從 0 算。用 `inspect_cells.py` 看座標和色盤編號。

四種寫法：

```json
{"legend": {"W": 7, "I": "#824784", "c": 3, ".": null},
 "rows": [45], "col": 53, "pattern": "  cWWWWccc"}
```
`rows` 裡的每一列，都從第 `col` 欄開始照 `pattern` 畫。`pattern` 的每個字元對到 `legend` 的顏色，空白表示那一格不改。`legend` 的值可以是色盤編號、`"#rrggbb"`（要是色盤裡有的顏色）或 `null`（透明）。連續很多列畫同一個圖樣時，寫 `"rows": [48, 51], "row_range": true` 表示第 48 到 51 列。

```json
{"cells": [[62, 66], [63, 66]], "color": 7}
{"cells": [[207, 107]], "copy_from": [208, 107]}
{"flood": [30, 58], "color": null}
```
`cells` 把列出的格子改成同一個顏色，或用 `copy_from` 取另一格的顏色。`flood` 從那一格往外，把相連的同色格子全部改掉，最常用來挖掉兩腿之間被包住的背景（`"color": null`）。

顏色不在色盤裡時腳本會中止，並告訴你最接近的顏色。真的需要新顏色（例如把眼睛換色）才在那一筆加 `"allow_new": true`。

修眼睛的做法：先 `inspect_cells.py --box ... --png` 看現況，對照原圖決定眼白、瞳孔、周圍膚色各佔哪些格子，兩隻眼睛用同一個圖樣（或左右對稱的圖樣），一列一列寫成 pattern。圖樣比眼睛大一圈，把周圍一圈膚色也寫進去，才能蓋掉歪掉的邊緣。

修正之後用 `--reuse` 重跑（立繪和圖表都有），不會重新找網格和取樣，幾秒就好。

## animations：動作

給 `build_animation.py` 用。一個清單，每個動作在最終圖表佔一列，照清單順序排。

```json
{"name": "walk_right", "section": "walk", "frame_ms": 100}
{"name": "turnaround", "frames": ["front", "side_right", "back", "side_left"], "frame_ms": 400}
{"name": "walk_left", "mirror": "walk_right"}
{"name": "walk_down", "step": {"base": "front", "cycle": "walk"}, "frame_ms": 100}
{"name": "walk_up", "step": {"base": "back", "cycle": "walk", "swap_sides": true}, "frame_ms": 100}
{"name": "idle_down", "frames": ["front"]}
{"name": "expressions", "section": "expr"}
```

- `section`：整個區塊依序當畫格。`frames`：指定畫格名稱（可以重複、可以跨區塊）。
- `mirror`：左右鏡射另一個動作（要寫在它後面），速度沿用。鏡射是以錨點 x 為軸。
- `step`：用一張站姿做簡化的踏步。`cycle` 是 `walk`（8 格）或 `run`（6 格）；背面站姿加 `"swap_sides": true`。兩腿之間要有縫才分得出左右腳。
- `frame_ms`：每格毫秒數。不寫或 0 表示這一列是單張姿勢（表情、動作），不會輸出 GIF。
- `loop`：預設動畫會循環，`false` 是播一次停在最後一格。

輸出 JSON 裡畫格的命名：動畫是 `動作名_0`、`動作名_1`…；單張姿勢的列沿用來源畫格的名稱；只有一格的動作用動作名。

沒有寫 `animations` 時，每個區塊各成一列。

## 常見問題

**切出來的小人數量不對。** 看 `NAME_extract_check.png`。少了：小人太小被當成雜物（調低 `min_pixels`），或顏色太接近背景（調低 `bg_tolerance`）。多了：說明文字或道具被當成小人（縮小 `box` 避開，或調高 `min_pixels`）。兩個小人黏在一起時腳本會依寬度切開，切的位置不對就把那個區塊拆成兩個 `box`。

**小人被裁掉、警告「放不進畫格」。** 加大 `frame`，`anchor` 跟著改。

**同一個動畫裡頭忽大忽小。** 那個區塊不該用 `"height"`（姿勢高度不一），改用 `{"head_of": ...}` 對齊到站姿的區塊。

**顏色太多。** 來源圖每個小人的顏色略有出入是正常的（50 格高的小人常見 40–60 色）。設 `palette_from` 對到立繪的色盤可以減少；還是太多就調大 `palette_snap`。

**白底圖表：眼白或白衣服破洞。** 設 `"enclosed": "keep"`，再把兩腿之間的背景用 `flood` 挖掉。

**輪廓外面有一圈灰白的格子。** 設 `trim_fringe`；剩下的零星幾格用 `cells` 加 `"color": null` 去掉。

**格線疊圖看起來每格裡有四個小色塊。** 格距大了一倍，加 `pitch_hint`。反過來，一個色塊被切成四格就是小了一半。

**大圖（4K 以上）的立繪找網格很慢。** 先用一小塊試出格距，再用 `pitch` 固定格距，只搜尋起點。
