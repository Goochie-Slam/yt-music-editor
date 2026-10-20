# YT Music Editor — Bàn giao dự án

> Ngày: 2026-10-20 · Người giao: Product Owner (anh Duy) · Bản soạn: Claude (QA / orchestrator cũ)
> Đọc file này trước, rồi tới `PROJECT-OVERVIEW.md` → `REQUIREMENTS.md` → `CODING-GUIDE.md`.

---

## 1. Dự án trong 30 giây

App **chạy local trên Windows** (backend Python + giao diện trên trình duyệt) để làm video playlist nhạc 1–3 tiếng cho YouTube:

**① Thư viện** (lấy audio từ file / link, cắt tracklist, xuất MP3) → **② Mix** (kéo thả, transition, normalize) → **③ Video** (nền, effect, overlay, sóng nhạc, tên bài) → **④ Xuất** (render MP4 bằng NVENC, chunk + resume).

Máy mục tiêu: PC Windows 11, **RTX 3050 6GB**, 32 GB RAM, 12 luồng CPU.

---

## 2. Trạng thái hiện tại

| Milestone | Nội dung | Trạng thái |
|---|---|---|
| Thiết kế | Requirements v0.3, UI/UX v0.3, mockup HTML, coding guide | ✅ Xong |
| **M0** — Benchmark render | Đo trên RTX 3050 thật → chốt cách render A (D-21) | ✅ Xong, đã merge |
| **M1** — Khung app | Backend FastAPI, frontend React, project + autosave + undo, CI | ✅ Xong, đã merge (PR #1) |
| **M2** — Thư viện | Nhập file / thư mục / kéo thả, link + playlist (yt-dlp), cắt tracklist, xuất MP3 | 🟡 **Code xong, CHƯA merge** — xem §4 việc đầu tiên |
| M3 — Mix | Danh sách mix, transition editor, preset, normalize, trim, nghe thử, xuất mix MP3, chapters | ⬜ |
| M4 — Video core | Renderer GLSL, nền / artwork / fit, visualizer, chữ, canvas + timeline layer | ⬜ |
| M5 — Effect & Overlay | 6 effect P1, 3 loại overlay, 6 blend mode, preset style A–F | ⬜ |
| M6 — Xuất | Hàng đợi render, chunk + resume, ước tính, render thử 30s | ⬜ |
| M7 — Hoàn thiện | Bản portable Windows, dọn cache, chạy lại toàn bộ acceptance | ⬜ |

**Mã nguồn:** `github.com/Goochie-Slam/yt-music-editor`
- `main` = M0 + M1.
- Nhánh `claude/audio-video-editor-app-8ssfmv` = `main` + M2 (4 commit, ~5.100 dòng, 129 test backend + 37 test frontend pass trên Linux).

Ước lượng còn lại (1 dev full-time có kinh nghiệm Python + React): **M3 ~2 tuần · M4 ~3 tuần · M5 ~1,5 tuần · M6 ~1,5 tuần · M7 ~1 tuần ≈ 9 tuần**.

---

## 3. Danh sách chức năng & trạng thái

Ký hiệu: ✅ xong · 🟡 một phần · ⬜ chưa làm. Ưu tiên: **P1** = MVP · P2 = bản sau · P3 = để sau. Chi tiết từng ID: `REQUIREMENTS.md` §3–4.

### 3.1 Thư viện & lấy audio (M2)

| ID | Chức năng | Ưu tiên | Trạng thái |
|---|---|---|---|
| F1.1 | Kéo thả nhiều file / thư mục; mọi định dạng FFmpeg đọc được (mp4 mkv mov avi webm flv wmv mp3 wav flac m4a aac ogg opus wma aiff…). Dán đường dẫn file / thư mục cũng được | P1 | ✅ |
| F1.2 | Dán 1 hoặc nhiều link (YouTube, SoundCloud, Mixcloud, mọi site yt-dlp hỗ trợ). Link playlist → bảng tick chọn bài | P1 | ✅ (chưa thử với YouTube thật) |
| F1.3 | Mỗi bài hiện: tên, nguồn, định dạng, thời lượng, bitrate, trạng thái (đang tải % / xử lý / xong / lỗi + lý do tiếng Việt) | P1 | ✅ |
| F1.4 | Tick chọn → xuất hàng loạt **MP3 320 kbps CBR, không tag**, mẫu tên `{index} - {title}` sửa được | P1 | ✅ |
| F1.5 | Cắt 1 file dài theo tracklist dán vào (`mm:ss Tên` / `h:mm:ss Tên`), preview từng đoạn, báo lỗi từng dòng → "Cắt & thêm vào Mix" hoặc "Chỉ xuất MP3" | P1 | ✅ |
| F1.5b | Đoạn cắt tự vào Thư viện; tinh chỉnh điểm cắt ± vài giây bằng trim ở tab Mix | P1 | 🟡 vào Thư viện ✅ · trim → M3 |
| F1.6 | Nút "Thêm vào Mix" | P1 | ✅ |
| F1.7 | Tối đa 3 tác vụ nặng song song, có hủy | P1 | ✅ |
| F1.8 | Cảnh báo bitrate nguồn thấp (≤ 160 kbps, chỉ với nguồn lossy) | P1 | ✅ |
| F1.9 | Nút cập nhật yt-dlp trong Cài đặt | P1 | ✅ |
| F1.10 | Cache: file đã tải / đã giải mã không xử lý lại | P1 | ✅ |
| F1.11 | Không nén lossy nhiều lần: mọi xử lý đọc từ WAV lossless trong cache, MP3 chỉ tạo ở bước xuất | P1 | ✅ |

### 3.2 Mix & Transition (M3)

| ID | Chức năng | Ưu tiên | Trạng thái |
|---|---|---|---|
| F2.1 | Danh sách bài dọc, kéo thả đổi thứ tự, xóa, nhân bản | P1 | ⬜ |
| F2.2 | Mỗi bài: số thứ tự, tên hiển thị (sửa được), thời lượng sau trim, mini waveform | P1 | ⬜ |
| F2.3 | Thanh Overview cả mix (block bài, vùng transition, mốc giờ), click để nhảy | P1 | ⬜ |
| F2.4 | Footer: tổng số bài, tổng thời lượng (đã trừ overlap), dung lượng ước tính | P1 | ⬜ |
| F2.5 | Shuffle, sắp theo tên | P3 | ⬜ |
| F2.6 | Chip transition giữa 2 bài (tên preset + thời lượng), click mở editor | P1 | ⬜ |
| F2.7 | Transition Editor: 2 waveform chồng nhau + đường cong fade, kéo handle chỉnh `fadeOut` / `fadeIn` / `overlap`, có ô số | P1 | ⬜ |
| F2.8 | Nghe thử ~8s trước → ~8s sau điểm nối ngay trong trình duyệt | P1 | ⬜ |
| F2.9 | Chọn preset; sửa tham số → chip hiện "(đã chỉnh)" | P1 | ⬜ |
| F2.10 | Lưu / sửa / xóa preset của user; 5 preset mặc định không xóa được | P1 | 🟡 API backend + 5 preset ✅ · UI ⬜ |
| F2.11 | Áp dụng cho tất cả / các điểm nối đã chọn | P1 | ⬜ |
| F2.12 | Validate: fade / overlap ≤ 50% bài ngắn hơn, báo đỏ trên chip | P1 | 🟡 hàm tính ✅ · UI ⬜ |
| F2.13 | Fade-in đầu mix / fade-out cuối mix (mặc định 2s / 5s) | P1 | ⬜ |
| F2.14 | Normalize từng bài về −14 LUFS (chọn −16 / −12), đo 2-pass, cache | P1 | ⬜ |
| F2.15 | Limiter cuối mix, true-peak −1 dBTP | P1 | ⬜ |
| F2.16 | Hiện LUFS gốc, cảnh báo bài lệch > 6 LU | P2 | ⬜ |
| F2.17 | Tự cắt khoảng lặng đầu / cuối (−50 dBFS, ≥ 0.5s) | P1 | ⬜ |
| F2.18 | Trim tay bằng handle trên waveform, nghe thử điểm cắt | P1 | ⬜ |
| F2.19 | Gain riêng từng bài ±6 dB | P2 | ⬜ (đã có trường trong data model) |
| F2.20 | Xuất 1 file MP3 320 kbps cho cả mix | P1 | ⬜ |
| F2.21 | Xuất `chapters.txt` (`00:00 Tên bài`), mốc = giữa vùng crossfade | P1 | 🟡 hàm tính mốc ✅ · xuất ⬜ |
| F2.22 | Kiểm tra chapters theo luật YouTube (bắt đầu 00:00, ≥ 3 mốc, mỗi đoạn ≥ 10s) | P1 | 🟡 hàm kiểm tra ✅ · UI ⬜ |

Mô hình transition (đã chốt, D-02): mỗi điểm nối có `fadeOut`, `fadeIn`, `overlap` (> 0 = crossfade, ≤ 0 = khoảng lặng), `curveOut` / `curveIn` (equal-power mặc định · linear · log · s-curve). 5 preset: Smooth Blend, Quick Mix, Long Dissolve, Radio Segue, Fade & Breathe.

### 3.3 Video (M4 + M5)

| ID | Chức năng | Ưu tiên | Trạng thái |
|---|---|---|---|
| F3.1 | Khung 16:9 (1920×1080) hoặc 9:16; một project xuất được cả hai | P1 | ⬜ |
| F3.2 | Preview trên canvas đồng bộ audio, tua được | P1 | ⬜ |
| F3.3 | Hiện safe area YouTube / Shorts | P2 | ⬜ |
| F3.4–F3.6 | Nền: ảnh tĩnh · carousel (đổi theo giây hoặc theo bài, crossfade) · video loop (crossfade điểm loop) | P1 | ⬜ |
| F3.7–F3.9 | Fit mode khi lệch tỉ lệ: Blur fill / Solid color / Crop fill; chỉnh blur 0–60, độ tối 0–80%. Artwork là element riêng (40–150%, bo góc, bóng, viền) | P1 | ⬜ |
| F3.10–F3.15 | 6 effect P1: Slow Zoom / Ken Burns · Film Grain · Glow / Bloom · Floating Dust · Snowfall · Bokeh / Light Leak | P1 | ⬜ (bản thử trong `bench/`) |
| F3.16–F3.18 | VHS / Chromatic · Fog / Smoke · Rain | P2 | ⬜ |
| F3.20 | Parallax 2.5D (cần AI tách lớp) | P3 | ⬜ |
| F3.21–F3.22 | Bật / tắt, sắp thứ tự effect; cảnh báo khi bật > 3 effect | P1 | ⬜ |
| F3.23–F3.24 | Preset style A–F (Late-Night R&B, Bossa Nova Café, Party Remix, Christmas, Lofi/Sad, Synthwave) + lưu preset của user | P1 | ⬜ |
| F3.25 | Glow / Zoom phản ứng theo bass | P2 | ⬜ |
| F3.26 | Effect trên nền ảnh tĩnh loop liền mạch, không giật | P1 | ⬜ |
| F3.27–F3.31 | Sóng nhạc: 3 loại (Bars, Waveform, Circular) × 3 style = 9 style; màu, opacity, kích thước, vị trí, độ nhạy, độ mượt; ảnh giữa Circular; tắt được | P1 | ⬜ |
| F3.32 | Now Playing: tên bài đang phát, tự đổi khi đổi bài, fade / slide | P1 | ⬜ |
| F3.33–F3.34 | Tiêu đề playlist · Logo / watermark | P1 | ⬜ |
| F3.35 | Thanh progress bài hiện tại | P2 | ⬜ |
| F3.36–F3.37 | Text style (≥ 6 font tiếng Việt, cỡ, màu, shadow, outline, letter-spacing); kéo thả, snap lưới | P1 | ⬜ |
| F3.38–F3.49 | **Timeline layer** dưới canvas hiện MỌI element (gồm vòng loop): zoom, chọn đồng bộ canvas ↔ timeline ↔ Inspector, kéo 2 đầu thanh đổi thời gian, mắt ẩn / hiện, vạch điểm loop, nút "Xem chỗ nối loop", vị trí lưu riêng 16:9 / 9:16 | P1 | ⬜ |
| F3.50 | Kéo header track đổi thứ tự chồng lớp | P2 | ⬜ |
| F3.51 | Keyframe animation | P3 | ⬜ (PO: chưa làm giai đoạn này) |
| F3.52–F3.58 | **Overlay (bắt buộc MVP):** video (mp4 / mov / webm, có alpha, loop + crossfade) · PNG · màu / gradient / vignette; 6 blend mode; opacity, thời gian, nhiều overlay; ghép ở bước cuối, không nằm trong vòng loop nền | P1 | ⬜ |
| F3.59–F3.60 | Fit / vị trí overlay; đổi thứ tự overlay | P2 | ⬜ |

### 3.4 Xuất & Render (M6)

| ID | Chức năng | Ưu tiên | Trạng thái |
|---|---|---|---|
| F4.1 | Cài đặt output: 16:9 / 9:16 / cả hai · **1080p mặc định**, 1440p, 4K · 30 / 60fps · chất lượng Nhẹ / Cân bằng / Cao | P1 | ⬜ |
| F4.2 | Tự dò encoder (NVENC → fallback x264), H.264 + AAC | P1 | 🟡 dò NVENC ✅ · encode ⬜ |
| F4.3 | Render thử 30 giây ở vị trí bất kỳ | P1 | ⬜ |
| F4.4 | Ước tính dung lượng + thời gian trước khi render | P1 | ⬜ |
| F4.5 | Hàng đợi render: nhiều job, %, ETA, hủy, mở thư mục | P1 | ⬜ |
| F4.6 | Render theo chunk 5 phút → tắt máy giữa chừng thì resume | P1 | ⬜ |
| F4.7 | Job vẫn chạy khi đóng tab; mở lại thấy tiến độ | P1 | 🟡 hạ tầng job ✅ |
| F4.8 | Output kèm theo: `video.mp4`, `mix.mp3`, `chapters.txt` | P1 | ⬜ |
| F4.9 | Thông báo Windows khi xong | P2 | ⬜ |
| F4.10 | Kiểm tra ổ trống trước khi render (tính cả chunk tạm ≈ 2× file) | P1 | ⬜ (đã có cho import / xuất MP3) |

### 3.5 Project & Preset

| ID | Chức năng | Ưu tiên | Trạng thái |
|---|---|---|---|
| F5.1 | Project = 1 thư mục (`project.json` + cache). Tạo / mở / lưu / nhân bản | P1 | 🟡 nhân bản ⬜ |
| F5.2 | Autosave + Undo / Redo ≥ 50 bước | P1 | ✅ (100 bước) |
| F5.3 | Preset global; export / import `.json` | P1 | 🟡 preset transition ✅ · export / import ⬜ |
| F5.4 | Home: project gần đây + thumbnail | P1 | 🟡 thumbnail ⬜ |
| F5.5 | Template project (setting video không gồm bài) | P2 | ⬜ |

### 3.6 Yêu cầu phi chức năng

| ID | Yêu cầu | Trạng thái |
|---|---|---|
| N1 | Windows 10/11. Bản portable: giải nén → `Start.bat` → tự mở trình duyệt, đã kèm Python, FFmpeg, yt-dlp, **Deno** | 🟡 `Start.bat` bản dev (cần uv + Node 22) · portable → M7 |
| N2 | Offline trừ tải link | ✅ tới M2 |
| N3 | Tốc độ render trên RTX 3050: 1080p ≥ 3× realtime · 1440p ≥ 2× · 4K ≥ 0.7× (benchmark đo được 4.75× / 3.04× / 0.97×) | 🟡 đã đo prototype · kiểm lại ở M6 |
| N4 | Xuất mix MP3 3 tiếng ≤ 5 phút | ⬜ M3 |
| N5 | UI mượt với 100 bài; mở Transition Editor < 300ms | ⬜ M3 |
| N6 | Preview giống bản render (cùng shader) | ⬜ M4 |
| N7 | Render 3 tiếng không rò bộ nhớ, RAM backend < 4 GB | ⬜ M6 |
| N8 | Cache audio ~4 GB / 3 tiếng; hiện dung lượng + nút dọn | 🟡 nút dọn → M7 |
| N9 | Chữ tiếng Việt đúng trên preview và video | ⬜ M4 |
| N10 | Chỉ bind 127.0.0.1, chặn Host / Origin lạ | ✅ |

### 3.7 Acceptance test MVP (`REQUIREMENTS.md` §8)

| # | Kịch bản | Milestone | Trạng thái |
|---|---|---|---|
| 1 | Playlist YouTube 20 bài + 10 file local (mkv, flac, m4a) → xuất 25 MP3 320 kbps không lỗi | M2 | ⬜ chờ PO chạy trên máy thật |
| 2 | Cắt mix 2 tiếng theo tracklist 30 dòng → 30 đoạn đúng mốc (≤ 0.1s) → thêm vào Mix | M2 | 🟡 đã thử 6 phút / 4 đoạn (lệch 24ms) · chờ file thật |
| 3 | Mix 40 bài, mỗi điểm nối 1 preset, chỉnh tay 3 điểm, lưu 1 preset, nghe thử từng điểm | M3 | ⬜ |
| 4 | Âm lượng đều ±1 LU quanh −14 LUFS, không clip ở vùng crossfade | M3 | ⬜ |
| 5 | Render 16:9 nền ảnh dọc (blur fill) + preset B + Circular Bars + Now Playing, chạy hết 2h45 | M4–M6 | ⬜ |
| 6 | Tab Video: mọi element hiện trên timeline, click canvas chọn đúng track, kéo đổi vị trí / thời gian, "Xem chỗ nối loop" | M4 | ⬜ |
| 7 | Overlay `rain_on_glass.mp4` (Screen 45%) + gradient đáy + khung PNG; loop không giật | M5 | ⬜ |
| 8 | Tắt app khi render 60% → mở lại → resume | M6 | ⬜ |
| 9 | `chapters.txt` dán vào YouTube nhận đúng chapters | M3 | ⬜ |

---

## 4. Workflow giao việc

### 4.1 Vai trò

| Vai trò | Ai | Làm gì |
|---|---|---|
| Product Owner | Anh Duy | Chốt requirement, test trên máy thật, **bấm merge PR** |
| Developer | Người nhận bàn giao | Code theo milestone, mở PR, sửa theo review |
| QA / Reviewer | Người PO chỉ định (có thể là chính dev khác hoặc AI) | Review PR theo `CODING-GUIDE.md` §10.3, chạy test, báo Approve / Request changes |

### 4.2 Việc đầu tiên (tuần 1, trước khi code M3)

1. **Đọc tài liệu** theo thứ tự: `HANDOFF.md` → `PROJECT-OVERVIEW.md` → `REQUIREMENTS.md` → `UI-UX.md` + mở `ui-mockup.html` → `CODING-GUIDE.md` → `DECISIONS.md`.
2. **Dựng môi trường** (`CODING-GUIDE.md` §4): Python 3.12 + uv, Node 22, FFmpeg; chạy toàn bộ test cho ra xanh.
3. **Chốt M2:** mở PR từ nhánh `claude/audio-video-editor-app-8ssfmv` vào `main` → CI phải xanh trên **windows-latest** (đến giờ M2 mới chỉ chạy trên Linux) → sửa nếu đỏ.
4. **PO thử M2 trên máy thật** bằng `packaging\windows\Start.bat` (cần uv + Node 22):
   - dán 1 playlist YouTube thật khoảng 20 bài;
   - dán 1 set Mixcloud / YouTube dài, cắt theo tracklist;
   - xuất MP3.

   Lỗi nào cũng chụp màn hình kèm câu báo lỗi. Đạt acceptance 1 và 2 thì **PO merge**.
5. Rồi mới bắt đầu M3.

### 4.3 Vòng làm việc mỗi milestone

```
PO giao milestone (ID chức năng ở §3)
  → Dev tạo nhánh  feat/m3-<việc>  từ main mới nhất
  → Code + test (CODING-GUIDE §8: unit, integration với file sinh bằng FFmpeg lavfi, e2e)
  → Chạy kiểm tra local:  ruff · mypy (+ --platform win32) · pytest · eslint · tsc · vitest · build
  → Mở PR theo template (.github/pull_request_template.md):
       ID requirement đã làm · cách đã test · ảnh chụp UI cạnh mockup · chỗ lệch spec + lý do
  → CI xanh trên Windows + Linux
  → QA review (Approve / Request changes, mỗi lỗi có file:dòng + cách tái hiện)
  → PO thử trên máy thật (milestone có UI hoặc render) → PO merge
```

- **PR nhỏ:** nên dưới 500 dòng (không tính file sinh tự động); một PR làm một việc. M2 đã vi phạm (~5.100 dòng), không lặp lại.
- **Requirement mơ hồ** → hỏi PO trong PR / issue, không tự đoán rồi làm.
- **Quyết định ảnh hưởng lâu dài** (đổi thư viện, format file, kiến trúc) → thêm dòng vào `DECISIONS.md` trong cùng PR.
- **Muốn thêm tính năng ngoài P1** → đề xuất riêng, không gộp vào PR đang làm.

### 4.4 Definition of Done (tóm tắt `CODING-GUIDE.md` §11)

- Đủ ID requirement đã nhận, hoặc ghi rõ phần chưa làm và lý do.
- Có test theo §8.1; CI xanh trên windows-latest.
- Không lỗi ruff / mypy / ESLint / tsc.
- Chuỗi UI nằm trong `vi.json`; lỗi hiện bằng tiếng Việt dễ hiểu.
- Đã thử với đường dẫn có dấu tiếng Việt và khoảng trắng.
- Tác vụ dài: có tiến độ, hủy được, không khóa UI.
- Đổi schema → có migration và đã sinh lại type (`npm run gen:types`).

### 4.5 Quy tắc cứng — vi phạm là Request changes

1. Gọi FFmpeg / yt-dlp **chỉ qua `core/proc.py`**, list argument, **không bao giờ `shell=True`**.
2. **Không nén lossy chồng lớp:** mọi xử lý đọc từ WAV cache; chỉ `audio/export.py` tạo MP3 / AAC.
3. **Frontend là nơi duy nhất ghi `project.json`.** Job nền trả kết quả qua job event, không sửa project (D-24).
4. Effect / overlay / visualizer là **hàm thuần của thời gian `f(t)`** — không cập nhật trạng thái theo từng frame (để chunk, resume và preview ra cùng một frame).
5. **Preview = Render:** shader GLSL dùng chung ở `shared/shaders/`, gain curve dùng chung (`curves.py` ↔ `curves.ts`, cùng kiểm bằng `shared/fixtures/curves.json`).
6. Server chỉ bind `127.0.0.1`.
7. **Không commit nhạc / video / ảnh có bản quyền.** Fixture test sinh bằng FFmpeg lavfi.

---

## 5. Kế hoạch từng milestone còn lại

| Milestone | Phạm vi (ID) | Gợi ý tách PR | Xong khi |
|---|---|---|---|
| **M3 — Mix** (~2 tuần) | F2.1–F2.22, F1.5b | ① peaks waveform (D-31) + đo loudness 2-pass · ② danh sách mix kéo thả + overview + footer · ③ Transition Editor + preset UI + validate · ④ nghe thử bằng Web Audio · ⑤ auto trim + trim tay · ⑥ mixer streaming + limiter + xuất mix MP3 + chapters | Acceptance 3, 4, 9; mix 40 bài xuất ≤ 5 phút (N4) |
| **M4 — Video core** (~3 tuần) | F3.1–F3.9, F3.27–F3.49 | ① loader shader dùng chung (WebGL2 + moderngl) + golden test · ② nền / artwork / fit / carousel / video loop · ③ spectrum precompute + 9 visualizer · ④ chữ (skia-python), Now Playing, logo · ⑤ canvas + Inspector · ⑥ timeline layer | Golden frame test đạt; preview ≈ render (N6); acceptance 6 |
| **M5 — Effect & Overlay** (~1,5 tuần) | F3.10–F3.15, F3.21–F3.26, F3.52–F3.58 | ① 6 effect `f(t)` loop liền mạch · ② overlay video (NVDEC) / PNG / màu, 6 blend mode · ③ preset A–F | Acceptance 7; frame 0 ≡ frame cuối vòng loop |
| **M6 — Xuất** (~1,5 tuần) | F4.1–F4.10 | ① encoder NV12 + PBO → NVENC (theo `bench/run_bench.py`) · ② chunk + resume + concat + mux audio 1 lần · ③ hàng đợi + ước tính + render thử 30s | Acceptance 5, 8; N3 + N7 với mix 3 tiếng thật trên máy PO |
| **M7 — Hoàn thiện** (~1 tuần) | N1, N8 | Bản portable (Python embedded + FFmpeg + yt-dlp + **Deno** + font + frontend build), dọn cache, chạy lại toàn bộ §3.7 | PO giải nén → chạy được trên máy sạch |

> M4 dùng kết quả benchmark: render **cách A** (vẽ mọi thứ mỗi frame, D-21), đọc frame NV12 bằng PBO, encode NVENC, decode overlay bằng NVDEC. GPU chỉ dùng 17–27% → tối ưu sau này nhắm vào phía CPU (decode, pipe), không phải shader.

---

## 6. Việc còn treo & rủi ro đã biết

| # | Vấn đề | Ai xử lý | Khi nào |
|---|---|---|---|
| 1 | **M2 chưa chạy CI trên Windows và chưa thử YouTube / SoundCloud thật** (môi trường dev cũ bị chặn mạng tới các trang này) | Dev mở PR · PO test | Tuần 1 |
| 2 | YouTube bắt buộc yt-dlp có JavaScript runtime. Bản dev dùng Node 22; **bản portable phải kèm Deno** (D-27) | Dev | M7 |
| 3 | YouTube có thể báo "xác minh chống bot" → app báo lỗi tiếng Việt, khuyên cập nhật yt-dlp. Đăng nhập / cookies nằm **ngoài phạm vi** | PO quyết nếu cần | Khi gặp |
| 4 | Cache WAV float32 nặng ~4 GB / mix 3 tiếng (D-23); 4K 3 tiếng ≈ 40 GB file video + chunk tạm | Dev (nút dọn cache, kiểm ổ trống) | M6–M7 |
| 5 | Giả định chưa được PO xác nhận chính thức: A2 (playlist → tick chọn), A3 (sửa tên trong app, không ghi tag), A6 (UI tiếng Việt), A7 (định nghĩa 3 loại overlay) | PO | Trước M4 |
| 6 | N3 mới đo bằng prototype 60s; chưa có lần render liền 3 tiếng (nóng máy, rò bộ nhớ) | Dev + PO | M6 |
| 7 | Bitrate của stream audio trong file `.mkv` có video thường không đọc được → hiện "—" | Dev (tùy chọn) | Khi rảnh |

---

## 7. Bản đồ tài liệu & code

| Cần gì | Xem ở đâu |
|---|---|
| Chức năng đầy đủ, ID, acceptance | `docs/REQUIREMENTS.md` |
| Màn hình, hành vi UI, design token | `docs/UI-UX.md` + `docs/ui-mockup.html` (mở bằng trình duyệt) |
| Stack, cấu trúc repo, data model, quy tắc, test, milestone | `docs/CODING-GUIDE.md` |
| Vì sao làm như vậy (D-01 … D-31) | `docs/DECISIONS.md` |
| Thông số effect | `docs/visual-effects-reference.md` |
| Benchmark GPU + prototype renderer | `bench/` (`run_bench.py`, kết quả ở `bench/archive/`) |
| Backend | `backend/app/` — `api/` (router mỏng) · `audio/` (ingest, ytdlp, export, tracklist, curves, timeline) · `core/` (proc, jobs, projects…) · `models/` (pydantic = nguồn schema) |
| Frontend | `frontend/src/` — `features/library` (M2), `store/` (project + undo/redo, jobs), `api/` (client + type sinh tự động), `i18n/vi.json` |
| Chạy trên Windows | `packaging/windows/Start.bat` |
