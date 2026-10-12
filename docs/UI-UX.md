# YT Music Editor — UI/UX Design v0.1

> v0.2 — đã cập nhật theo feedback lần 1 (timeline layer cho tab Video, cắt tracklist → mix, 2K/4K).
> Mockup tương tác: mở [`ui-mockup.html`](./ui-mockup.html) bằng trình duyệt (không cần cài gì).
> Requirement IDs (F1.x, F2.x…) tham chiếu [`REQUIREMENTS.md`](./REQUIREMENTS.md).

---

## 1. Nguyên tắc thiết kế

1. **Đi theo quy trình, không theo tool.** App có 4 bước tuần tự: **Thư viện → Mix → Video → Xuất**. Mỗi bước là 1 tab có đánh số. Quay lại bước trước lúc nào cũng được, không mất dữ liệu.
2. **Danh sách, không phải timeline.** Mix 3 tiếng gồm 40 bài: nếu dùng timeline ngang kiểu Premiere, ở mức zoom đọc được chỉ thấy 2–3 bài và phải cuộn ngang liên tục. Dạng **danh sách dọc + chip transition** cho thao tác nhanh hơn nhiều; thanh Overview phía trên vẫn cho thấy cả mix theo tỉ lệ thời gian.
3. **Chỉnh chi tiết chỉ khi cần.** Mặc định dùng preset. Tham số nâng cao (curve, LUFS…) nằm trong phần "Nâng cao" thu gọn.
4. **Nghe / xem thử ngay.** Transition nghe thử trong < 1s (Web Audio). Video preview trực tiếp trên canvas; trước khi render dài có "Render thử 30s".
5. **Không bao giờ mất việc.** Autosave, Undo/Redo, render resume theo chunk.
6. **Giao diện tối (dark)** — chuẩn của app biên tập media, giúp đánh giá màu video chính xác hơn.
7. **Desktop-first:** tối thiểu 1280×720. Không tối ưu cho mobile (app local trên Windows).

---

## 2. Cấu trúc thông tin

```
Home (danh sách project)
└── Project
    ├── Top bar: tên project · trạng thái autosave · Undo/Redo · hàng đợi render · Settings
    ├── ① Thư viện       — nhập file/link, cắt tracklist, xuất MP3 hàng loạt
    ├── ② Mix            — sắp thứ tự, transition, normalize, trim, xuất mix MP3
    ├── ③ Video          — canvas + timeline layer: mọi element (chữ, logo, visualizer, effect, artwork, nền, loop)
    └── ④ Xuất           — cài đặt output, ước tính, render thử, hàng đợi
Settings (global): folder mặc định, yt-dlp update, encoder, cache, quản lý preset
```

---

## 3. Layout chung

```
┌────────────────────────────────────────────────────────────────────────┐
│ ◆ YT Music Editor │ Chill Night Mix ✓ Đã lưu │ ① ② ③ ④ │ ↶ ↷ │ ⏳1 │ ⚙ │  ← Top bar 52px
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│                     Nội dung tab (full height)                         │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ ▶ ━━━━━━━●━━━━━━━━━━━━━━━  01:12:44 / 02:47:12   Bài 14: Rainy Window  │  ← Player bar (tab ②)
└────────────────────────────────────────────────────────────────────────┘
```

- **Player bar** ở tab Mix: phát mix hiện tại, tua, hiện bài đang phát. Ở tab Video, transport nằm trên đầu timeline. Phím `Space` = play/pause ở cả hai tab.
- **Indicator hàng đợi** (⏳) luôn hiện khi có job chạy; click mở drawer tiến độ từ bất kỳ tab nào.

---

## 4. Màn hình chi tiết

### ① Thư viện

```
┌──────────────────────────────────────────────┬─────────────────────────┐
│ [ Thêm file / link ]  [ Cắt theo tracklist ] │ XUẤT MP3                │
│ ┌──────────────────────────────────────────┐ │ Chất lượng: 320kbps CBR │
│ │  Kéo thả file/folder vào đây             │ │ Folder: D:\Music\Out [] │
│ │  hoặc dán link (mỗi dòng 1 link)         │ │ Tên: {index} - {title}  │
│ │  [__________________________] [Lấy]      │ │                         │
│ └──────────────────────────────────────────┘ │ Đã chọn: 12 bài · 48 MB │
│ ☑ # Tên            Nguồn     Dài   kbps Tt   │ [ Xuất 12 file MP3 ]    │
│ ☑ 1 Midnight Coffee YouTube  3:42  160 ✓     │ [ Thêm vào Mix → ]      │
│ ☑ 2 Rainy Window    a.flac   4:05  950 ✓     │                         │
│ ☐ 3 Velvet Sky      SoundCl. 3:18  128 ⚠     │                         │
│ ☑ 4 ...             ...       ...      ⟳45%  │                         │
└──────────────────────────────────────────────┴─────────────────────────┘
```

- **Dán link playlist** → mở modal danh sách bài, có "Chọn tất cả" và ô tìm kiếm → "Thêm N bài".
- Cột trạng thái: `⟳ %` đang tải/xử lý · `✓` xong · `⚠` bitrate thấp (hover xem giải thích) · `✕` lỗi (hover xem lý do + nút Thử lại).
- **Cắt theo tracklist** (sub-tab): chọn file nguồn → textarea dán tracklist → bảng preview các đoạn (tên, bắt đầu, kết thúc, độ dài) báo lỗi từng dòng → nút chính **"Cắt & thêm vào Mix →"**, nút phụ "Chỉ xuất MP3". Đoạn cắt giữ lossless trong cache, không qua MP3 trung gian.
- Phím tắt: `Ctrl+A` chọn tất cả, `Del` xóa khỏi thư viện (không xóa file gốc).

### ② Mix

```
┌───────────────────────────────────────────────────────────────┬────────────────┐
│ Normalize [-14 LUFS ▾] ☑   Auto trim lặng ☑   Mặc định: [Smooth Blend ▾]       │
│ OVERVIEW ▕██▓░██▓░███▓░██▓░██████▓░██▓░███▓░▏ (block = bài, ▓░ = transition)   │
├───────────────────────────────────────────────────────────────┤ TRANSITION     │
│ ⠿ 01  Midnight Coffee      ▁▃▅▇▅▃▁   3:42                     │ 01 → 02        │
│       ── ◆ Smooth Blend · 6s ──                               │                │
│ ⠿ 02  Rainy Window         ▁▃▅▇▅▃▁   4:05                     │ [Preset ▾]     │
│       ── ◆ Quick Mix · 2.5s ──  ← chip transition             │  ╲    ╱        │
│ ⠿ 03  Velvet Sky           ▁▃▅▇▅▃▁   3:18                     │   ╲  ╱         │
│       ── ◇ Fade & Breathe · lặng 1.5s ──                      │    ╳  ← kéo    │
│ ⠿ 04  ...                                                     │ Out [6.0]s     │
│                                                               │ In  [6.0]s     │
│                                                               │ Chồng [6.0]s   │
│                                                               │ ▸ Nâng cao     │
│                                                               │ [▶ Nghe thử]   │
│                                                               │ [Lưu preset]   │
│                                                               │ [Áp dụng tất cả]│
├───────────────────────────────────────────────────────────────┴────────────────┤
│ 40 bài · 2:47:12 · ~400 MB MP3        [ Xuất timestamps ☐ ]  [ Xuất mix MP3 ]  │
└────────────────────────────────────────────────────────────────────────────────┘
```

**Hành vi:**
- **Kéo thả** bằng handle `⠿`; khi đang kéo, chip transition ẩn đi để danh sách gọn lại. Thả xong, transition cũ **đi theo cặp bài cũ** nếu cặp đó còn tồn tại, cặp mới nhận preset mặc định.
- **Chip transition**: ◆ = crossfade (chồng), ◇ = có khoảng lặng. Viền đỏ = lỗi validate (F2.12). Chữ nghiêng "(đã chỉnh)" khi lệch khỏi preset.
- **Shift+click** nhiều chip → panel bên phải sửa hàng loạt.
- **Click một bài** → panel phải chuyển sang **Track Editor**: waveform lớn + handle trim in/out, LUFS gốc, gain.
- **Biểu đồ transition**: 2 waveform chồng nhau theo trục thời gian. Kéo cạnh phải bài trên = `fadeOut`, kéo cạnh trái bài dưới = `fadeIn`, kéo cả bài dưới sang ngang = `overlap` (sang trái là chồng, sang phải là lặng). Ô số đồng bộ 2 chiều với handle.
- **Nghe thử**: phát từ 8s trước điểm bắt đầu transition tới 8s sau điểm kết thúc; playhead chạy trên biểu đồ. Phím `P`.

### ③ Video

```
┌────────────┬──────────────────────────────────────────────┬──────────────────┐
│ THÊM       │ [16:9][9:16]  ☐ Safe area      [Render thử]  │ INSPECTOR        │
│ [+Text]    │ ┌──────────────────────────────────────────┐ │ (element đang    │
│ [+Ảnh/Logo]│ │ ┌Tên playlist┐                 (LOGO)    │ │  chọn)           │
│ [+Effect]  │ │ Chill Night Mix                          │ │                  │
│ [+Viz]     │ │ blur ░░░│ ARTWORK │░░░  ◎ visualizer     │ │ Tên playlist     │
│            │ │ ĐANG PHÁT                                │ │ Nội dung [____]  │
│ PRESET     │ │ 4. Rainy Café                            │ │ Font [▾] [700▾]  │
│ [A][B]     │ └──────────────────────────────────────────┘ │ Cỡ ━━●━━         │
│ [C][D]     │                                              │ Màu ■ ☑ Shadow   │
│ [E][F]     │                                              │ Vị trí X[25] Y[27]│
├────────────┴──────────────────────────────────────────────┤ Hiển thị        │
│ ▶ 01:12:44 / 02:33:34  Bài 20     Zoom[Toàn bộ|10p|2p] ⟲Loop│ 00:00 → 01:01:55│
│ Thời gian  │00:00   00:15   00:30   00:45   01:00   01:15 … │ ☐ Đến hết video │
│ CHỮ & HÌNH │                                              │                  │
│ ♪ Now Play │▕1▏2▕3▏4▕5▏6▕7▏8▕9▏… (1 đoạn / bài)             │                  │
│ T Tên PL   │[▌Chill Night Mix          ▐]  ← kéo 2 đầu     │                  │
│ T Phụ đề   │[▌Tuyển tập nhẹ nhàng ……………………………………………▐]   │                  │
│ ◎ Logo     │[▌Logo kênh ………………………………………………………………………▐]   │                  │
│ VISUALIZER │                                              │                  │
│ ▁▃ Viz     │[Circular · Radial Bars · theo audio ……………]   │                  │
│ EFFECT     │                                              │                  │
│ ✦ Zoom     │[Slow Zoom · loop 60s │    │    │    │    │ ]  │                  │
│ ✦ Grain    │[Film Grain · loop 30s│ │ │ │ │ │ │ │ │ │ │ ]  │                  │
│ HÌNH NỀN   │                                              │                  │
│ ▣ Artwork  │[artwork.jpg · 9:16 · tĩnh suốt video ………]    │                  │
│ ▦ Nền      │[Blur fill · LOOP 60s × 154 │  │  │  │  │  ]   │                  │
│ AUDIO      │                                              │                  │
│ ♫ Mix      │[Bài 1][Bài 2][Bài 3]… (chỉ xem)              │                  │
└────────────┴──────────────────────────────────────────────┴──────────────────┘
```

**Nguyên tắc: video = các element chồng lên nhau, và mọi element đều nhìn thấy được trên timeline.** Không có thứ gì được render mà user không thấy hoặc không sửa được.

**Timeline layer** (dưới canvas, cao ~40% màn hình):
- Track chia theo **5 nhóm**, từ trên xuống = từ lớp trên cùng xuống lớp dưới cùng: **Chữ & hình → Visualizer → Effect → Hình nền → Audio**.
- Mỗi track có header (icon · tên · mắt ◉/○) và thanh theo thời gian. Nhãn thanh **dính theo khi cuộn ngang**, không bị trôi mất.
- **Zoom**: Toàn bộ (cả mix trong 1 màn) / 10 phút / 2 phút. Khi đang phát và đã zoom, timeline tự cuộn theo playhead.
- Click thước thời gian hoặc vùng trống của track → tua tới đó.

| Track | Hiển thị | Thao tác trên timeline |
|---|---|---|
| **Now Playing** | 1 đoạn / bài, xen kẽ 2 sắc độ, có tên bài khi đủ rộng | Click 1 đoạn → tua tới bài đó + Inspector cho sửa tên bài đó |
| **Tên playlist / Phụ đề / Text** | Thanh từ lúc bắt đầu đến lúc kết thúc hiển thị, ghi nội dung text | **Kéo đầu trái / phải** = đổi lúc hiện / ẩn · kéo giữa = dời cả đoạn |
| **Logo / Ảnh** | Như text | Như text |
| **Visualizer** | Thanh suốt video, ghi loại · style | Click = chọn |
| **Mỗi effect** | Thanh suốt video, **vạch dọc tại mỗi chu kỳ loop**, ghi "loop 60s" | Click = chọn, Inspector mở đúng effect đó |
| **Artwork** | Ảnh tĩnh: 1 thanh · **Carousel: mỗi ảnh 1 đoạn khớp với bài** · Video: vạch tại mỗi lần lặp clip | Click = chọn |
| **Nền** | Fit mode + **"LOOP 60s × 154 — render 1 lần rồi lặp"**, vạch trắng tại mỗi điểm nối. Carousel / video: cảnh báo "không loop được, render toàn bộ" | Click = chọn |
| **Mix audio** | Block từng bài + vùng crossfade | Chỉ xem; Inspector có nút "Sửa ở tab Mix →" |

**Chọn đồng bộ 3 chiều** — canvas ↔ timeline ↔ Inspector luôn cùng một element:
- Click element trên canvas → track tương ứng sáng lên, Inspector chuyển sang element đó. Canvas vẽ **khung nét đứt + nhãn tên** quanh element đang chọn.
- Click track trên timeline → canvas hiện khung chọn quanh element đó.
- Click vùng trống trên canvas → chọn **Nền**.

**Canvas**: hover element → con trỏ thành ✥; **kéo để đổi vị trí**. Ô X / Y (%) trong Inspector cập nhật theo. Vị trí lưu **riêng cho 16:9 và 9:16**.

**Inspector theo element:**
- **Text** (Tên playlist, Phụ đề, Text thêm): nội dung · font (có dấu tiếng Việt) · độ đậm · cỡ (px ở 1080p) · màu · shadow · animation vào · X/Y · **thời gian hiển thị** (bắt đầu / kết thúc / "Đến hết video") · Xóa (chỉ với text thêm).
- **Now Playing**: tên hiển thị của bài đang chọn (sửa ở đây = sửa trong Mix, không ghi tag) · format · dòng nhãn "ĐANG PHÁT" · font · animation khi đổi bài · cỡ · màu · X/Y.
- **Logo / Ảnh**: file · kích thước · opacity · X/Y · thời gian hiển thị.
- **Visualizer**: Bars / Waveform / Circular · 3 style có thumbnail chạy thật · màu gradient · kích thước (cảnh báo khi > 40%) · độ nhạy · opacity · 9 điểm neo · X/Y.
- **Effect**: danh sách đủ 11 effect (P2/P3 hiện mờ kèm badge); effect đang chọn được viền nổi bật; cảnh báo khi bật > 3.
- **Artwork**: Ảnh / Carousel / Video loop · media · đổi ảnh theo bài / theo thời gian · crossfade điểm loop video · kích thước 40–150% · bo góc · đổ bóng · viền · X/Y.
- **Nền**: Blur fill / Solid color / Crop fill · blur · độ tối · màu · **khối "Loop nền"**: chu kỳ, số lần lặp, giải thích vì sao render nhanh · nút **⟲ Xem chỗ nối loop**.

**Khác:**
- **⟲ Xem chỗ nối loop** (trên timeline + trong Inspector Nền): nhảy tới 3s trước điểm nối gần nhất rồi tự phát, để soi xem có giật không.
- **Preset style A–F**: áp dụng bộ effect + visualizer, sau đó chọn sẵn track effect đầu tiên để chỉnh tiếp.
- **＋ Text** thêm text hiển thị 5 phút tính từ playhead (thường dùng cho câu kêu gọi subscribe, lời chào…). **＋ Ảnh / Logo** thêm được nhiều. MVP chỉ có **1 visualizer** / video.
- Ở tab Video, player bar chung bị ẩn; nút play và thời gian nằm trên đầu timeline.
- **Ngoài phạm vi:** keyframe animation (element bay vào, đổi vị trí theo thời gian). Có cái này là thành video editor tổng quát rồi — không phải mục tiêu của app.

### ④ Xuất

```
┌───────────────────────────────────────┬────────────────────────────────┐
│ CÀI ĐẶT                               │ ƯỚC TÍNH                       │
│ Khung hình  ☑ 16:9  ☐ 9:16            │ Thời lượng      2:47:12        │
│ Độ phân giải [1080p ▾] (2K/4K tùy chọn)│ Dung lượng      ~6.8 GB        │
│ Chất lượng  (Nhẹ)(●Cân bằng)(Cao)     │ Thời gian render ~1h12m *      │
│ FPS [30|60]  Encoder [RTX 3050 NVENC ▾]│ Ổ D: còn 214 GB  ✓             │
│ Folder      D:\Videos\Out  [Đổi]      │ * từ render thử gần nhất       │
│ FILE ĐI KÈM ☑ mp4 ☑ mix.mp3 ☐ chapters│ [ Render thử 30s tại 01:12:00 ]│
│                                       │ [ ▶ BẮT ĐẦU RENDER ]           │
├───────────────────────────────────────┴────────────────────────────────┤
│ HÀNG ĐỢI                                                                │
│ Chill Night Mix · 16:9  ████████████░░░░░░  64% · chunk 22/34 · còn 26m [Hủy] │
│ Chill Night Mix · 9:16  Chờ                                         [Hủy] │
│ Jazz Café Vol.2 · 16:9  ✓ Xong 10/10 21:04            [Mở folder] [Xem] │
└─────────────────────────────────────────────────────────────────────────┘
```

- Độ phân giải: **1080p mặc định**. Chọn 1440p → ghi chú "YouTube dùng codec tốt hơn cho video ≥1440p, người xem 1080p cũng thấy nét hơn; render lâu ~1.8×". Chọn 4K → cảnh báo "render ~4×, file ~4×". Ước tính cập nhật ngay.
- Nút "Bắt đầu render" bị khóa (kèm lý do) khi: thiếu bài, lỗi transition, thiếu nền, ổ không đủ dung lượng.
- Job bị gián đoạn hiện **"Tiếp tục từ chunk 22"** thay cho thanh progress.
- Bật `chapters` → hiện preview nội dung bên dưới, kèm nút Copy.

---

## 5. Luồng chính (happy path)

```
Home → Tạo project "Chill Night Mix"
 → ① dán link playlist YouTube → tick 30 bài → kéo thêm 10 file flac → "Thêm vào Mix"
 → ② chọn mặc định "Smooth Blend" → kéo đổi thứ tự → chỉnh 3 điểm nối → nghe thử → lưu preset "My Chill"
 → ③ chọn nền ảnh dọc → Fit: Blur fill → Preset B (Bossa Nova) → Visualizer Circular/Radial → bật Now Playing
 → ④ Render thử 30s → OK → Bắt đầu render (16:9 + chapters)
 → đóng trình duyệt, đi làm việc khác → nhận thông báo xong → mở folder
```

---

## 6. Trạng thái & phản hồi

| Tình huống | Hiển thị |
|---|---|
| Đang tải / xử lý | Progress trong dòng + spinner nhỏ, không chặn UI |
| Lỗi 1 item | Dòng đỏ + lý do bằng tiếng người ("Video riêng tư", "Link không hỗ trợ") + Thử lại |
| Lỗi validate | Viền đỏ ngay tại chỗ + tooltip, không popup |
| Hành động phá hủy (xóa bài, xóa preset) | Thực hiện ngay + toast "Đã xóa · **Hoàn tác**" (5s), không hỏi xác nhận |
| Thao tác dài (normalize lần đầu 40 bài) | Banner phía trên tab: "Đang phân tích âm lượng 12/40" — vẫn làm việc khác được |
| Mất kết nối backend | Banner đỏ cố định "Mất kết nối app — đang thử lại…" |

---

## 7. Phím tắt

| Phím | Chức năng |
|---|---|
| `Space` | Play / Pause |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / Redo |
| `Ctrl+S` | Lưu (dù đã autosave — cho yên tâm) |
| `1` – `4` | Chuyển tab (khi không gõ trong ô text) |
| `P` | Nghe thử transition đang chọn |
| `←` / `→` | Tua 5s · `Shift` + mũi tên: nhảy bài |
| `Del` | Xóa item đang chọn |

---

## 8. Visual style

| Token | Giá trị | Dùng cho |
|---|---|---|
| `--bg` | `#0f1115` | Nền app |
| `--panel` | `#171a21` | Panel |
| `--panel-2` | `#1f232c` | Card, input |
| `--border` | `#2a2f3a` | Viền |
| `--text` | `#e7e9ee` | Chữ chính |
| `--muted` | `#8b93a5` | Chữ phụ |
| `--accent` | `#7c5cff` | Nút chính, chọn |
| `--accent-2` | `#22d3ee` | Transition, waveform |
| `--ok` / `--warn` / `--err` | `#34d399` / `#fbbf24` / `#f87171` | Trạng thái |

- Font UI: **Inter** (hỗ trợ tiếng Việt). Số / thời gian dùng `tabular-nums` để không nhảy khi chạy.
- Bo góc 8px; khoảng cách theo lưới 4px.
- Màu trạng thái luôn đi kèm icon / chữ — không dùng màu làm tín hiệu duy nhất.
