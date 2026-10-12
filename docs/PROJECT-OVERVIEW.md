# YT Music Editor — Project Overview

> Dành cho developer mới tham gia dự án. Đọc file này trước, sau đó đọc [`CODING-GUIDE.md`](./CODING-GUIDE.md).
> Cập nhật: 2026-10-12 · Trạng thái: **M1 (khung app) xong · M0 chờ chạy benchmark trên máy RTX 3050**

---

## 1. Dự án là gì

App **chạy local trên Windows** để sản xuất **video playlist nhạc dài 1–3 tiếng** đăng YouTube (kiểu "Chill Night Mix", "Jazz Café Playlist"…).

Một người dùng, không cloud, không tài khoản. Giao diện là web app chạy ở `localhost`, mở bằng trình duyệt; backend Python + FFmpeg làm toàn bộ việc nặng.

**Quy trình 4 bước = 4 tab của app:**

```
① Thư viện ──► ② Mix ──► ③ Video ──► ④ Xuất
lấy audio      sắp bài,    nền, chữ,     render MP4
từ file/link   transition  overlay,      + mix.mp3
cắt tracklist  normalize   effect, sóng  + chapters.txt
xuất MP3                   nhạc
```

| Bước | Làm gì | Ví dụ |
|---|---|---|
| ① Thư viện | Lấy audio từ file local (mọi định dạng FFmpeg đọc được) hoặc link (YouTube, SoundCloud, Mixcloud… qua yt-dlp). Cắt 1 file dài thành nhiều bài theo tracklist. Xuất MP3 320kbps hàng loạt | Dán playlist YouTube 20 bài + kéo 10 file FLAC |
| ② Mix | Danh sách kéo thả, transition riêng cho từng điểm nối (crossfade hoặc fade → lặng → fade), 5 preset, normalize -14 LUFS, trim | 40 bài, 2h45m |
| ③ Video | Canvas + **timeline layer**: artwork (ảnh / carousel / video loop), nền blur, overlay (video / PNG / gradient), effect (zoom, grain, bụi, tuyết…), visualizer (9 style), Now Playing, tên playlist, logo | 16:9 nền blur từ ảnh dọc |
| ④ Xuất | Render 1080p (mặc định) / 1440p / 4K, NVENC, theo chunk, resume được | MP4 + mix.mp3 + chapters.txt |

---

## 2. Tài liệu — đọc theo thứ tự

| # | File | Vai trò | Ai sửa |
|---|---|---|---|
| 1 | **`PROJECT-OVERVIEW.md`** (file này) | Bức tranh tổng thể, vai trò, quy trình | Orchestrator |
| 2 | [`REQUIREMENTS.md`](./REQUIREMENTS.md) | **Nguồn sự thật** cho chức năng. Mọi requirement có ID (`F2.7`, `N3`…) | Orchestrator, sau khi Product Owner duyệt |
| 3 | [`UI-UX.md`](./UI-UX.md) | Spec từng màn hình, hành vi, phím tắt, design token | Orchestrator |
| 4 | [`ui-mockup.html`](./ui-mockup.html) | Mockup tương tác — mở bằng trình duyệt. **Tham khảo giao diện, không phải code để copy** | Orchestrator |
| 5 | [`CODING-GUIDE.md`](./CODING-GUIDE.md) | Stack, cấu trúc repo, data model, quy tắc code, test, milestone, quy trình PR | Orchestrator + Developer |
| 6 | [`DECISIONS.md`](./DECISIONS.md) | Nhật ký quyết định (đã chốt gì, vì sao) | Ai ra quyết định thì ghi |
| 7 | [`visual-effects-reference.md`](./visual-effects-reference.md) | Thư viện effect và preset style A–F | Product Owner |

> Khi tài liệu mâu thuẫn nhau: `REQUIREMENTS.md` > `UI-UX.md` > `ui-mockup.html`. Gặp mâu thuẫn thì **hỏi**, đừng tự chọn.

---

## 3. Vai trò

| Vai trò | Ai | Trách nhiệm |
|---|---|---|
| **Product Owner** | Anh (chủ dự án) | Quyết định phạm vi và ưu tiên. Duyệt requirement. Merge PR cuối cùng. Chạy benchmark và test trên máy thật (Windows + RTX 3050 6GB) |
| **Orchestrator & QA** | Claude | Giữ tài liệu thống nhất, chia milestone/task, trả lời câu hỏi về requirement, **review mọi PR** (code + đối chiếu requirement + chạy test), xác nhận acceptance criteria |
| **Developer** | Bạn | Viết code + test theo `CODING-GUIDE.md`, mở PR nhỏ, ghi rõ requirement ID đã làm và cách đã test |

**Luồng làm việc:**

```
Orchestrator tạo task (issue) có requirement ID + tiêu chí xong
        │
        ▼
Developer làm trên branch feature ──► mở PR (theo template)
        │
        ▼
QA (Claude) review: code · test · đối chiếu requirement ──► yêu cầu sửa / đạt
        │
        ▼
Product Owner duyệt & merge vào main
```

Chi tiết: mục 10 của [`CODING-GUIDE.md`](./CODING-GUIDE.md).

---

## 4. Kiến trúc (tóm tắt)

```
┌──────────── Trình duyệt (http://127.0.0.1:PORT) ─────────────┐
│ React + TypeScript + Vite                                     │
│ 4 tab · Zustand store · Web Audio (nghe thử transition)       │
│ WebGL2 preview — dùng CHUNG shader GLSL với renderer          │
└──────────────────────▲────────────────────────────────────────┘
                       │ REST (JSON) + WebSocket (tiến độ job)
┌──────────────────────┴────────────────────────────────────────┐
│ Python 3.12 · FastAPI · job queue (process riêng)             │
│  audio/  : ingest, yt-dlp, tracklist, loudness, mixer, FFT    │
│  video/  : scene → moderngl (GLSL) → NVENC qua FFmpeg         │
│  project : project.json + cache (WAV lossless, peaks, FFT)    │
└──────────────────────┬────────────────────────────────────────┘
                       │ subprocess
          FFmpeg / ffprobe · yt-dlp.exe (bundle sẵn)
```

**5 khái niệm phải nắm trước khi code:**

1. **Transition = 3 số** `fadeOut`, `fadeIn`, `overlap` (+ curve). `overlap > 0` là crossfade, `overlap < 0` là khoảng lặng. Không có 2 code path riêng.
2. **Không nén lossy nhiều lần.** Mọi xử lý nội bộ dùng WAV lossless trong cache. MP3/AAC chỉ tạo ở bước xuất cuối.
3. **Video = các element chồng lên nhau**, mọi element đều hiện trên timeline (chữ, logo, visualizer, overlay, effect, artwork, nền, audio).
4. **Effect là hàm thuần của thời gian** `f(t)` — không giữ state từ frame trước. Nhờ vậy render theo chunk, resume, preview và render mới cho ra cùng một frame.
5. **Loop nền:** với nền ảnh tĩnh, nền + effect lặp theo chu kỳ (ví dụ 60s). Overlay, visualizer và chữ ghép ở bước cuối. Có dùng "render 1 vòng rồi lặp" hay không sẽ do **Spike S1** quyết định.

---

## 5. Phạm vi

**Trong MVP (P1):** mọi requirement P1 trong `REQUIREMENTS.md`. Tóm tắt:
- Lấy audio từ file / link / playlist, cắt tracklist → mix, xuất MP3 320kbps
- Mix kéo thả, transition + 5 preset + lưu preset, normalize, trim, nghe thử, xuất mix + chapters
- Video: timeline layer, artwork ảnh/carousel/video, fit mode (blur/solid/crop), 6 effect, **overlay video/PNG/gradient**, 9 visualizer, Now Playing, text, logo, preset style A–F, 16:9 & 9:16
- Xuất: 1080p/1440p/4K, NVENC, chunk + resume, render thử 30s, hàng đợi

**Chưa làm (P2/P3):** VHS, Fog, Rain procedural, keyframe animation, Parallax 2.5D, đổi thứ tự overlay, gain từng bài, template project.

**Không bao giờ làm:** vượt DRM, đăng nhập nền tảng, upload YouTube tự động, beat-matching kiểu DJ, chạy trên cloud.

---

## 6. Trạng thái & roadmap

| Milestone | Nội dung | Trạng thái |
|---|---|---|
| Thiết kế | Requirements v0.3, UI/UX v0.3, mockup | ✅ Xong |
| **M0 — Spike S1** | Benchmark render trên RTX 3050 6GB → chốt kiến trúc render | 🟡 Script xong (`bench/`) — **chờ PO chạy trên máy thật** |
| M1 — Skeleton | Repo, CI, backend + frontend khung, project/autosave, đóng gói Windows | ✅ Xong |
| M2 — Thư viện | Ingest, yt-dlp, tracklist, xuất MP3 | ⬜ |
| M3 — Mix | Transition, preset, normalize, trim, nghe thử, xuất mix | ⬜ |
| M4 — Video core | Renderer, scene, artwork/nền, visualizer, chữ, canvas, timeline | ⬜ |
| M5 — Effect & Overlay | 6 effect, 3 loại overlay, preset A–F | ⬜ |
| M6 — Xuất | Hàng đợi, chunk, resume, NVENC, ước tính | ⬜ |
| M7 — Hoàn thiện | Đóng gói, acceptance test toàn bộ | ⬜ |

Chi tiết từng milestone và ước lượng công: mục 9 của `CODING-GUIDE.md`.

---

## 7. Rủi ro lớn nhất (đọc kỹ)

| Rủi ro | Vì sao quan trọng | Cách xử lý |
|---|---|---|
| **Render chậm** trên RTX 3050 6GB | Mix 3 tiếng = 324.000 frame. Nếu render mất 4–5 tiếng ở 1080p thì app không dùng được | **M0 làm trước tiên.** Không viết UI video trước khi có số liệu |
| **Preview ≠ bản render** | User chỉnh trên preview, render ra khác thì mất lòng tin | Shader GLSL dùng chung, effect là hàm thuần `f(t)`, có test so khớp frame |
| **Phình phạm vi** | Thiết kế đã lớn hơn "app đơn giản" nhiều | Chỉ làm đúng P1. Muốn thêm gì phải qua Product Owner và ghi vào `DECISIONS.md` |
| **yt-dlp hỏng** khi YouTube đổi hệ thống | Mất chức năng lấy link | Dùng `yt-dlp.exe` riêng, có nút cập nhật |
| **Bản quyền** | Nhạc / footage của người khác trên kênh có kiếm tiền | Ngoài phạm vi kỹ thuật. **Không commit nhạc hay footage có bản quyền vào repo**, kể cả làm test |

---

## 8. Môi trường mục tiêu

| Hạng mục | Giá trị |
|---|---|
| OS | Windows 10/11 64-bit |
| Máy Product Owner | NVIDIA **RTX 3050 6GB** (NVENC + NVDEC) |
| Chạy | Bản portable: giải nén → `Start.bat` → tự mở trình duyệt |
| Mạng | Chỉ bind `127.0.0.1`; offline được (trừ tải link) |
| Ngôn ngữ UI | Tiếng Việt |
