# YT Music Editor — UI/UX Design v0.1

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
    ├── ③ Video          — nền, effect, visualizer, chữ; preview
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
│ ▶ ━━━━━━━●━━━━━━━━━━━━━━━  01:12:44 / 02:47:12   Bài 14: Rainy Window  │  ← Player bar (tab ② ③)
└────────────────────────────────────────────────────────────────────────┘
```

- **Player bar** dùng chung ở tab Mix và Video: phát mix hiện tại, tua, hiện bài đang phát. Phím `Space` = play/pause.
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
- **Cắt theo tracklist** (sub-tab): chọn file nguồn → textarea dán tracklist → bảng preview các đoạn (tên, bắt đầu, kết thúc, độ dài) báo lỗi từng dòng → "Xuất N đoạn".
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
┌──────────────┬─────────────────────────────────────────┬──────────────────┐
│ LAYERS       │  [16:9] [9:16]   ☐ Safe area   Zoom 50% │ INSPECTOR        │
│ ◉ Chữ        │ ┌─────────────────────────────────────┐ │ (theo layer chọn)│
│   Now Playing│ │                                     │ │                  │
│   Tiêu đề    │ │          canvas preview             │ │ Visualizer       │
│ ◉ Visualizer │ │                                     │ │ [Bars][Wave][Circ]│
│ ◉ Effect (3) │ │   ▁▃▅▇▅▃▁  Now Playing: ...         │ │ ┌──┐┌──┐┌──┐    │
│   Slow Zoom  │ └─────────────────────────────────────┘ │ │ 1││ 2││ 3│    │
│   Grain      │  ▶ ━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │ └──┘└──┘└──┘    │
│   Dust       │    │   │   │   │   │  (mốc đổi bài)     │ Màu ■  Size ━●━  │
│ ◉ Nền        │                                         │ Vị trí [⊞ 9 neo] │
│ PRESET STYLE │                                         │                  │
│ [A][B][C]    │                                         │                  │
│ [D][E][F]    │                                         │                  │
└──────────────┴─────────────────────────────────────────┴──────────────────┘
```

**Hành vi:**
- **Layers** (trái): 4 nhóm cố định theo thứ tự từ trên xuống: Chữ → Visualizer → Effect → Nền. Mắt ◉ để ẩn/hiện. Effect trong nhóm kéo đổi thứ tự được.
- **Preset style A–F** (trái dưới): click = áp dụng effect + gợi ý visualizer. Có xác nhận nếu đang có chỉnh sửa tay.
- Bật effect thứ 4 → toast vàng: *"Guideline khuyên dùng 2–3 effect. Nhiều hơn dễ rối mắt và file nặng."* — không chặn.
- **Canvas**: click element để chọn, kéo để di chuyển, snap vào 9 điểm neo và safe area. Chọn element nào thì Inspector hiện đúng element đó.
- **Nền → Inspector**: loại (Ảnh / Carousel / Video) · danh sách media (kéo thả thứ tự cho carousel) · đổi ảnh: "mỗi X giây" / "theo bài" · **Fit mode**: Blur fill / Solid color / Crop fill · blur & độ tối · màu nền.
- Đổi **16:9 ↔ 9:16** giữ nguyên style, vị trí element tính theo neo (ví dụ "dưới-trái, cách lề 5%") nên tự thích ứng.
- Timeline mini dưới canvas có **mốc đổi bài**; hover hiện tên bài; click để tua tới đó xem Now Playing đổi.

### ④ Xuất

```
┌───────────────────────────────────────┬────────────────────────────────┐
│ CÀI ĐẶT                               │ ƯỚC TÍNH                       │
│ Khung hình  ☑ 16:9  ☐ 9:16            │ Thời lượng      2:47:12        │
│ Độ phân giải [1080p ▾]  FPS [30 ▾]    │ Dung lượng      ~6.8 GB        │
│ Chất lượng  (Nhẹ)(●Cân bằng)(Cao)     │ Thời gian render ~1h12m *      │
│ Encoder     [Tự động: NVIDIA NVENC ▾] │ Ổ D: còn 214 GB  ✓             │
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
