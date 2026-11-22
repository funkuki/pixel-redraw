# 提示詞範本

影像模型對英文提示詞的服從度比較穩定，所以範本用英文；角色描述可以先用中文和使用者確認，再翻成英文填進去。`{...}` 是要替換的部分。

提示詞存成文字檔（例如 `work/portrait_prompt.txt`），手動生成和 API 生成都用同一份。

## 立繪（第 2 步）

**立繪一定要附風格參照圖。** 只給文字的話，模型畫出來的頭身比、眼睛和格子大小每次都不一樣，和預設風格差很遠；附上參照圖才會穩定。參照圖在 `assets/`：

| 風格 | 參照圖 | 背景 |
|---|---|---|
| 色塊 Q 版 | `assets/ref_chibi_flat.png` | 黑 |
| 輪廓街拍 | `assets/ref_outline_street.png` | 白 |

兩張都是 1024×1024、已經是真正的像素圖（一格 9 px 和 7 px）。參照圖只用來定風格、比例和像素大小，角色本身要換掉，所以提示詞裡要寫明「不要照抄參照圖的髮型、服裝和顏色」。使用者有自己的風格參照圖時用他的；同一個系列的第二位角色起，改用第一位已經確認過的立繪（`_10x.png` 放在同色底上）當參照圖，系列會更一致。

角色描述要寫多細，可以看 `assets/prompt_sheet_chibi_flat.webp` 和 `assets/prompt_sheet_outline_street.webp`：每位角色一小段（髮型髮色、服裝、配件、手上的東西），加三四個主要顏色。向使用者說明要提供哪些設定時，也可以把這兩張圖給他看。

### 色塊 Q 版的範本

```
Japanese Cozy Pixel Art — Character Template
Create a charming Japanese-style pixel art character, matching the visual style of the provided reference image. Use the reference image ONLY for the art style, body proportions, eye style and pixel size. Do NOT copy its hairstyle, outfit, accessories or colors: the character is the one described in section 4.

1. ART STYLE
Japanese cozy pixel art, retro 16-bit RPG character sprite aesthetic, contemporary Japanese indie game character design.
* Cute, minimalist, nostalgic, and softly colored.
* Authentic hand-crafted pixel art, NOT a pixelated digital illustration.
* Clean, consistent square pixel grid.
* Every visible pixel must follow the same underlying grid spacing.
* Crisp, hard-edged pixel clusters with staircase-shaped contours.
* No anti-aliasing, no interpolated edges, no blurry pixels.
* Simple, readable shapes with carefully controlled pixel density.
* Soft pastel colors arranged in distinct, flat pixel clusters.
* Limited palette of approximately 12–16 colors per character.
* Two or three discrete shading levels per material.
* No smooth gradients, lighting effects, or dithering noise.
* Avoid thick black outlines; define shapes using darker local colors.

2. CHARACTER PROPORTIONS
* Super-deformed chibi proportions, approximately 2.3–2.5 heads tall.
* Oversized rounded head occupying approximately 45% of the total character height.
* Large, voluminous hairstyle with a softly rounded silhouette.
* Small, compact torso.
* Very short legs and small simplified feet.
* Tiny arms and hands represented by minimal pixel clusters.
* Symmetrical, front-facing neutral standing pose.
* Both feet resting on the same horizontal baseline.

3. FACIAL DESIGN
* Two oversized, square-shaped pixel eyes.
* Simple geometric pupils with small white pixel highlights.
* Eyes are widely spaced and positioned on the lower half of the face.
* Tiny or invisible nose.
* No visible mouth in the neutral expression.
* Soft, peaceful, approachable expression.
* Minimal facial detail.

4. CHARACTER DESIGN
Character: {角色描述}
Hair: {髮色、長度、形狀和髮型}
Eyes: {眼睛顏色}
Outfit: {上衣、下身、外套、鞋子}
Accessories: {帽子、包包、眼鏡或其他東西}
Color Palette: {主色和點綴色}
Personality: {gentle, curious, shy, playful…}

5. PIXEL GRID & RENDERING
Design the character as a small native-resolution pixel sprite, approximately 64 × 64 pixels, then enlarge it using nearest-neighbor scaling.
* Preserve a uniform logical pixel size.
* Every pixel edge aligns to the same square grid.
* All diagonal lines must be formed from deliberate square-pixel steps.
* Use small, intentional clusters of solid colors.
* Maintain consistent pixel density across the face, hair, clothing, and accessories.
* Do not introduce tiny subpixels or differently sized pixel blocks.
* Avoid excessive details that cannot be represented cleanly at native sprite resolution.

6. COMPOSITION
* One complete, full-body character.
* Centered composition.
* Pure solid black background (#000000).
* Generous empty space surrounding the character.
* No floor, shadows, environment, text, typography, frames, or decorative elements.
* Square image, 1:1 aspect ratio.

7. STRICT NEGATIVE CONSTRAINTS
Avoid smooth digital painting, vector illustration, anime line art, 3D, voxel art, isometric perspective, photorealism, soft focus, blurred pixels, anti-aliased outlines, mixed pixel sizes, irregular grid spacing, complex textures, dirty edges, color noise, smooth gradients, glowing effects, thick black outlines, realistic anatomy, and unnecessary detail.

FINAL REQUIREMENT:
The result must look like an authentic, hand-pixeled Japanese indie-game character sprite, with a consistent logical pixel grid, clean silhouettes, simplified facial features, harmonious pastel colors, and charming 2.5-head-tall proportions.
```

黑底的關係，角色身上不能有純黑；要黑髮、黑鞋的角色，在第 4 節寫成深灰或深藍（例如 `very dark navy, not pure black`）。

### 輪廓街拍的範本

附上 `assets/ref_outline_street.png` 一起給模型。

```
Create a high-quality MASTER CHARACTER SPRITE for a Japanese cozy pixel art fashion game, matching the visual style of the provided reference image. Use the reference image ONLY for the art style, body proportions, eye style and pixel size. Do NOT copy its hairstyle, outfit, accessories or colors: the character is the one described in section 1.

## 1. CHARACTER

Character name: {角色名稱}

Character description:
{角色描述}

Hairstyle: {髮型}
Hair color: {髮色}
Eye color: Light warm brown
Outfit: {服裝和顏色}
Footwear: {鞋子}
Accessories: {配件}
Personality: {個性}

Preserve every specified character feature exactly.

## 2. ART STYLE

Japanese cozy pixel art, retro 16-bit RPG character sprite aesthetic, contemporary Japanese indie game character design.

- Cute, minimalist, nostalgic, and softly colored.
- Authentic hand-crafted pixel art, NOT a pixelated digital illustration.
- Clean, consistent square pixel grid.
- Every visible pixel must follow the same underlying grid spacing.
- Crisp, hard-edged pixel clusters with staircase-shaped contours.
- No anti-aliasing, interpolated edges, or blurry pixels.
- Simple, readable shapes with carefully controlled pixel density.
- Soft, muted colors arranged in distinct flat pixel clusters.
- Limited palette of approximately 12–16 colors per character.
- Two or three discrete shading levels per material.
- No smooth gradients, lighting effects, or dithering noise.
- Avoid thick black outlines; define shapes using darker local colors.

## 3. CHARACTER PROPORTIONS

- Super-deformed chibi proportions, approximately 2.3–2.5 heads tall.
- Oversized rounded head with a compact, softly shaped body.
- Head occupies approximately 40–43% of total character height.
- Short arms and legs with simplified anatomy.
- Small hands and feet, clearly readable at sprite resolution.
- Softly rounded silhouette, slightly wider around the head and clothing.
- Consistent body proportions suitable for future sprite animation.

FACE:
- Large, simple, expressive pixel eyes.
- Light warm brown irises, not blue.
- Tiny nose and minimalist mouth.
- Gentle, relaxed, charming expression.
- Subtle pixel blush using the existing skin palette.
- Both eyes and facial features must align to the same pixel grid.

## 4. MASTER SPRITE POSE

- One single character only.
- Full-body standing pose.
- Slight three-quarter front view, with the face mostly facing forward.
- Neutral and relaxed posture.
- Both arms resting naturally at the sides, slightly separated from the torso.
- Both feet firmly resting on the same baseline.
- Both shoes fully visible.
- No walking, jumping, sitting, or exaggerated gestures.
- No perspective distortion or dynamic camera angle.
- Maintain clearly separated limbs and readable clothing silhouettes.

The pose must serve as a reliable reference for future character sheets, turnarounds, outfit variations, and walk-cycle animations.

## 5. CLOTHING & ACCESSORIES

- Follow the CHARACTER description exactly.
- Preserve the specified garment shapes, lengths, colors, and layering.
- Represent folds, seams, collars, buttons, and pockets with minimal pixel clusters.
- Accessories should remain clearly recognizable at small sprite sizes.
- Use consistent pixel density across hair, face, clothing, shoes, and accessories.
- Avoid excessively detailed patterns or noisy textures.

## 6. COLOR PALETTE

Japanese minimalist street fashion colors.

- Muted earthy tones.
- Warm neutrals and dusty pastels.
- Soft, nostalgic, low-saturation palette.
- Harmonious, carefully controlled color relationships.
- Two or three discrete tonal values per material.
- No harsh highlights, realistic lighting, or gradients.

Keep character colors consistent across future generations.

## 7. SPRITE CANVAS & COMPOSITION

- Design the character for a logical 96 × 128 pixel sprite canvas.
- Use one consistent square-pixel unit throughout the entire character.
- Render at a crisp integer upscale using nearest-neighbor scaling.
- Keep character centered horizontally.
- Leave generous transparent margins around the entire silhouette.
- Both feet aligned to a consistent baseline.
- No cropping of hair, shoes, or accessories.
- Transparent background preferred.
- No floor, scenery, props outside the specified accessories, or cast shadows.
- One sprite only, not a sprite sheet.

## 8. STRICT NEGATIVE CONSTRAINTS

Avoid:
- Mixed pixel sizes or inconsistent grid spacing.
- Anti-aliasing or soft pixel edges.
- Blurry outlines or interpolation.
- Pixelated high-resolution illustrations.
- Random isolated pixels.
- Dithering noise.
- Smooth gradients.
- Thick black outlines.
- 3D or voxel rendering.
- Realistic anatomy.
- Anime-style detailed eyes.
- Excessively long limbs.
- Deformed hands or extra fingers.
- Inconsistent shading directions.
- Background decorations.
- Text, labels, borders, UI elements, or watermarks.

FINAL OUTPUT:
One clean, polished, production-ready Japanese cozy pixel art MASTER SPRITE with consistent grid spacing, recognizable character identity, clear silhouette, and charming 2.3–2.5-head-tall proportions.
```

範本要求透明背景，但模型常常給白底，或把透明畫成灰白棋盤格。拿到圖先看背景：真的透明或白底就照 styles.md 用 `"remove_background": "border"`；畫成棋盤格的要重新生成，並把第 7 節的背景那兩行改成 `Pure solid white background (#FFFFFF).`。

### 其他風格的範本

自訂風格用這份比較短的範本，同樣要附一張風格參照圖（使用者提供的，或同系列已確認過的立繪）。

```
Match the visual style of the provided reference image: use it ONLY for the art style, body proportions, eye style and pixel size. Do NOT copy its hairstyle, outfit, accessories or colors.

A single full-body pixel-art character, front view, standing in a neutral pose with arms relaxed at the sides, centered in the image.

CHARACTER: {角色描述：髮型髮色、服裝、配件、手上的東西}
STYLE: {預設風格直接用 styles.md 裡的 STYLE 行；其他風格寫明頭身比、有沒有輪廓線、配色氣氛}

HARD RULES:
- True pixel art on ONE uniform square pixel grid. Every pixel-art pixel is a crisp, perfectly square, single flat color block with hard edges. No anti-aliasing, no gradients, no blur, no glow, no dithering, no drop shadow.
- The character is about {90–120} pixel-art pixels tall. Use a small palette of about 16 flat colors.
- The whole character is visible from the top of the hair or hat to the shoes, with empty margin on all sides.
- Background: one flat solid color {背景色，不能出現在角色身上，例如 pure black #000000 或 pure white #FFFFFF}. No floor, no ground shadow, no frame, no text.
- Eyes are simple flat blocks of {眼睛顏色} with a {眼白／高光的畫法}; both eyes are the same size and shape.
```

要注意的事：

- 背景色不能出現在角色身上。有黑色輪廓就不要黑底；穿白衣服就不要白底。
- 寫明角色高度大約幾格。不寫的話模型畫的格子大小很隨意。
- 眼睛的畫法寫得越具體越好（整塊單色、有沒有高光）。眼睛是重繪時最容易壞的地方，畫法越簡單越好修。

## 精靈圖表（第 3 步）

參考圖依序是：image 1 = `make_scale_ref.py` 做的比例參考圖；image 2（有的話）= 同一位角色已經生成、確認過的另一張圖表。

```
Image 1 is the exact character reference: it has the same dimensions as the image you will create, and it shows the character at the exact size and exact pixel scale that every sprite must have. {有 image 2 時：Image 2 is a finished sprite sheet of this same character: match its pixel size, sprite size, outline and shading style exactly.} Create a NEW pixel-art sprite sheet of the character in image 1 with the content listed below.

HARD RULES (most important):
- True pixel art on ONE uniform square pixel grid across the entire image. Every pixel-art pixel is a crisp, perfectly square, single flat color block with hard edges. No anti-aliasing, no gradients, no blur, no glow, no drop shadows, no dithering, no smooth curves.
- Pixel size check: one pixel-art pixel in your image must be exactly as large as one pixel-art pixel of the character in image 1 ({pitch}x{pitch} screen pixels). Do not draw finer or coarser pixels.
- Every sprite is the SAME scale: the character is about {height_cells} pixel-art pixels tall when standing, with the same proportions as image 1.
- Layout: exactly {rows} rows x {cols} columns, exactly {rows×cols} sprites, evenly spaced in an invisible grid. Every sprite shows the FULL body from the top of the hat or hair to the shoes; never crop a sprite. Feet of all sprites in a row are on the same horizontal baseline. Leave clear empty white space around every sprite; sprites MUST NOT touch or overlap each other.
- Background: pure flat white (#FFFFFF) everywhere. No floor, no ground shadow, no frame, no grid lines, no labels, no text, no numbers, no arrows, no motion lines.
- Keep the design identical to image 1 in every sprite: same outfit, same accessories, same colors, same outline. Use only the colors found in image 1. Do NOT add any item the character does not have in image 1.
- Face exactly like image 1: {眼睛的畫法}. Do NOT redraw the face in a different style.

CHARACTER: {角色描述}

SHEET CONTENT (left to right):
Row 1 — {這一列的內容，逐格列出}
Row 2 — {這一列的內容，逐格列出}
```

`{pitch}`、`{height_cells}`、`{rows}`、`{cols}` 用 `make_scale_ref.py` 印出的數字。

圖表背景用白色，是因為參考圖是白底，模型比較會照著畫；去背時用設定檔的 `"enclosed": "keep"` 處理白色衣物（見 config.md）。如果角色大面積是白色而且沒有輪廓線，改成角色身上沒有的顏色（參考圖的底色也要跟著改，目前 `make_scale_ref.py` 固定是白底，要另外處理）。

### 每一列內容的寫法

一張圖表 2 列 × 6 格是比較穩的版面。動作多就分成多張，每張各跑一次生成。下面是可以直接用的幾列：

```
standing turnaround, 6 views: front view, three-quarter front facing right, right side profile, three-quarter back facing right, back view, front view with a small wave.

front view, 6 frames: idle standing, idle with the body 1 pixel lower (breathing), eyes closed (blink), happy smile, surprised, shy looking down.

walk cycle facing right in strict side profile, 6 frames in order: right foot contact, down, passing, left foot contact, down, passing. Normal relaxed walking, NOT running: the body is upright, steps are short, one foot is always on the ground. The face is fully visible in every frame.

walk cycle straight toward the viewer, 6 frames in order: right foot contact, down, passing, left foot contact, down, passing. Every frame is the front-view sprite, changing ONLY the legs, feet and a 1-pixel body bounce. Both eyes and the whole face are visible in every frame.

walk cycle straight away from the viewer, full back view (the face is not visible), 6 frames in order: right foot contact, down, passing, left foot contact, down, passing. Changing ONLY the legs, feet and a 1-pixel body bounce.

run cycle facing right in strict side profile, 6 frames in order, body leaning forward, long strides, both feet off the ground in frames 3 and 6.

full body, 6 frames: sitting on the ground with legs forward, sitting with legs to the side, crouching to pick something up from the ground, reaching up with one hand, cheering with both arms up, bowing.
```

寫的時候記得：

- 只生成向右的走路和跑步，向左用鏡射。
- 走路循環要逐格寫出腳的狀態，並寫明「不是跑步」；不寫的話模型常常畫成跑步或每格都一樣。
- 正面、背面的走路要寫「只改腿、腳和 1 像素的起伏」，否則模型會把角色重新設計成別的比例。
- 禁止的東西要列出來（地板、陰影、文字、編號、動作線）。模型很愛加說明文字和編號，這些會被當成小人或黏在小人上。
- 生成的順序：先做站姿／轉身那一張，確認後拿它當其他張的 image 2。
