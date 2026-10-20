# YT Music Editor — Coding Guide

> Đọc [`PROJECT-OVERVIEW.md`](./PROJECT-OVERVIEW.md) trước. File này nói **làm thế nào**; `REQUIREMENTS.md` nói **làm cái gì**.
> Mọi chỗ ghi **PHẢI** là bắt buộc — QA sẽ chặn PR nếu vi phạm. Chỗ ghi *nên* là khuyến nghị.

---

## Mục lục

1. [Nguyên tắc](#1-nguyên-tắc)
2. [Tech stack](#2-tech-stack)
3. [Cấu trúc repo](#3-cấu-trúc-repo)
4. [Cài đặt & chạy](#4-cài-đặt--chạy)
5. [Data model — `project.json`](#5-data-model--projectjson)
6. [Backend: quy tắc kỹ thuật](#6-backend-quy-tắc-kỹ-thuật)
7. [Frontend: quy tắc kỹ thuật](#7-frontend-quy-tắc-kỹ-thuật)
8. [Test](#8-test)
9. [Milestone & task](#9-milestone--task)
10. [Quy trình làm việc, PR & QA](#10-quy-trình-làm-việc-pr--qa)
11. [Definition of Done](#11-definition-of-done)
12. [Những lỗi hay gặp — đừng mắc](#12-những-lỗi-hay-gặp--đừng-mắc)

---

## 1. Nguyên tắc

1. **Đúng trước, đẹp sau, nhanh sau cùng** — trừ tốc độ render, thứ phải đo ngay từ M0.
2. **Requirement ID là hợp đồng.** Code cho requirement nào thì ghi ID đó trong PR. Không có ID thì không làm — hỏi trước.
3. **Đơn giản.** Không thêm thư viện, abstraction hay tính năng "để sau dùng". Ba dòng code lặp lại tốt hơn một abstraction đoán trước tương lai.
4. **Preview = Render.** Cùng shader, cùng công thức gain curve, cùng dữ liệu FFT. Không bao giờ có hai cách tính riêng cho preview và render.
5. **Không mất việc của user.** Autosave, ghi file atomic, job resume được.
6. **Windows là nền tảng chính.** Code chạy được trên Linux/macOS để dev và chạy CI, nhưng chỉ cần chạy *đúng* trên Windows.

---

## 2. Tech stack

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Backend | **Python 3.12** · **FastAPI** · uvicorn · **pydantic v2** | Quản lý package bằng **uv** (`pyproject.toml` + `uv.lock`) |
| Audio | **FFmpeg / ffprobe** (subprocess) · **numpy** · **soundfile** | FFmpeg static build cho Windows, bundle sẵn |
| Tải link | **yt-dlp.exe** (bản standalone, gọi bằng subprocess) | Không dùng bản thư viện Python — bản `.exe` tự cập nhật được bằng `-U` (F1.9) |
| Render | **moderngl** (OpenGL 3.3 headless) · FFmpeg **h264_nvenc** | Chốt sau M0. Fallback: `libx264` |
| Text → texture | **skia-python** | Chỉ vẽ lại khi nội dung đổi (Now Playing đổi 1 lần / bài) |
| Frontend | **React 18** · **TypeScript** (strict) · **Vite** | Package manager: **npm** (`package-lock.json`) |
| State | **Zustand** + **immer** (undo/redo qua patches) | |
| Kéo thả | **dnd-kit** | |
| Preview | **WebGL2** (raw, không dùng three.js) · Web Audio API | |
| Style | CSS thuần + CSS variables (design token ở `UI-UX.md` §8) | Không dùng Tailwind / UI kit — mockup đã có token |
| Font | Be Vietnam Pro, Inter, Playfair Display, Montserrat, Lora, Quicksand (OFL) | **Bundle file font local**, không load từ Google Fonts (app phải chạy offline) |
| Test | pytest · Vitest · Playwright | |
| Lint | **ruff** (lint + format) · **mypy** · ESLint · Prettier · `tsc --noEmit` | |

> Thêm dependency mới vào một trong hai file `pyproject.toml` / `package.json` → **PHẢI** giải thích lý do trong PR. QA sẽ hỏi "có cần thật không".

---

## 3. Cấu trúc repo

```
yt-music-editor/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              # FastAPI app, bind 127.0.0.1, mount frontend build
│   │   ├── api/                 # router mỏng: validate → gọi service → trả về
│   │   │   ├── projects.py  library.py  mix.py  video.py
│   │   │   ├── render.py    presets.py  system.py  ws.py
│   │   ├── core/
│   │   │   ├── config.py        # đường dẫn app data, port, bin ffmpeg/yt-dlp
│   │   │   ├── proc.py          # wrapper subprocess DUY NHẤT (xem §6.2)
│   │   │   ├── jobs.py          # job queue, progress, hủy
│   │   │   ├── events.py        # pub/sub → WebSocket
│   │   │   ├── fsutil.py        # ghi atomic + backup, tên thư mục an toàn cho Windows
│   │   │   ├── projects.py      # folder project + danh sách gần đây
│   │   │   ├── presets.py       # preset transition có sẵn + của user
│   │   │   ├── tools.py         # version FFmpeg/yt-dlp, dò NVENC, self-test
│   │   │   ├── security.py      # chặn Host/Origin lạ (N10)
│   │   │   ├── errors.py        # AppError → {code, message_vi, detail}
│   │   │   └── util.py          # new_id, utcnow
│   │   ├── models/              # pydantic — NGUỒN SỰ THẬT của schema
│   │   │   ├── project.py  track.py  transition.py  element.py  render.py  preset.py
│   │   ├── audio/
│   │   │   ├── ingest.py        # probe + decode → WAV cache, mở rộng đường dẫn thư mục
│   │   │   ├── ytdlp.py         # tải link, playlist, cập nhật
│   │   │   ├── tracklist.py     # parse "mm:ss Tên" + cắt
│   │   │   ├── loudness.py      # loudnorm 2-pass, cache số đo
│   │   │   ├── silence.py       # auto trim
│   │   │   ├── curves.py        # công thức gain curve (dùng chung với frontend)
│   │   │   ├── timeline.py      # start / chapter time từ tracks + transitions
│   │   │   ├── mixer.py         # mix streaming theo block → WAV float
│   │   │   ├── peaks.py         # waveform peaks cho UI
│   │   │   ├── spectrum.py      # FFT từng frame cho visualizer
│   │   │   └── export.py        # MP3 320 không tag, mẫu tên file (M2) · AAC, chapters.txt (M3+)
│   │   ├── video/
│   │   │   ├── scene.py         # project → danh sách layer cần vẽ tại thời điểm t
│   │   │   ├── gl.py            # context moderngl, nạp shader, FBO, PBO readback
│   │   │   ├── layers/          # artwork.py bg.py effects.py overlay.py viz.py text.py
│   │   │   ├── encoder.py       # dò NVENC, pipe frame vào ffmpeg
│   │   │   └── chunks.py        # chia chunk, resume, concat, mux audio
│   │   └── presets/             # JSON preset có sẵn (transition, style A–F)
│   └── tests/                   # unit/ integration/ golden/
├── frontend/
│   ├── package.json  vite.config.ts  tsconfig.json
│   └── src/
│       ├── main.tsx  App.tsx
│       ├── api/                 # client REST + WebSocket, type sinh từ schema
│       ├── store/               # zustand slices: project, ui, jobs, history
│       ├── features/
│       │   ├── library/  mix/  video/  export/
│       ├── components/          # Button, Seg, Slider, Field… dùng chung
│       ├── gl/                  # WebGL2 renderer cho preview (đọc shared/shaders)
│       ├── audio/               # Web Audio preview transition, curves.ts
│       ├── i18n/vi.json         # MỌI chuỗi hiển thị
│       └── styles/tokens.css
├── shared/
│   ├── shaders/                 # *.glsl — một nguồn cho cả preview & render
│   ├── schema/project.schema.json   # sinh từ pydantic, KHÔNG sửa tay
│   └── fixtures/curves.json     # bảng giá trị curve để test chéo Py ↔ TS
├── bench/                       # Spike S1
├── packaging/windows/           # Start.bat, script build bản portable
├── docs/
└── .github/                     # PR template, CI workflow
```

**Quy tắc phụ thuộc giữa module:**
- `api/` chỉ gọi `audio/`, `video/`, `core/`, `models/`. Không chứa logic nghiệp vụ.
- `audio/` và `video/` **không import `api/`**, không biết gì về HTTP.
- Chỉ `core/proc.py` được gọi `subprocess`.
- Frontend chỉ gọi backend qua `src/api/`.

---

## 4. Cài đặt & chạy

### Yêu cầu
- Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22 LTS
- FFmpeg ≥ 7 có `h264_nvenc` (Windows: bản static build "full"); `yt-dlp.exe`
- Để trong `backend/bin/` (đã gitignore) hoặc chỉ đường dẫn qua biến môi trường `YTME_FFMPEG`, `YTME_YTDLP`

### Lệnh

```bash
# backend
cd backend && uv sync && uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8765 --reload
# frontend (dev, proxy /api → 8765)
cd frontend && npm ci && npm run dev
# kiểm tra trước khi mở PR
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run mypy --platform win32 && uv run pytest
cd frontend && npm run lint && npm run typecheck && npm test
# sinh lại schema + TS types sau khi sửa models/
cd backend && uv run python -m app.models.export_schema && cd ../frontend && npm run gen:types
```

### Chạy trên Windows (Product Owner)

Double-click `packaging\windows\Start.bat`. Lần đầu, script tự tải FFmpeg và yt-dlp vào `backend\bin\` rồi build giao diện, nên cần có [uv](https://docs.astral.sh/uv/) và Node 22. Bản portable không cần cài gì sẽ có ở M7.

### Dữ liệu app
- Cài đặt, preset, log: `%APPDATA%\YTMusicEditor\` (Linux dev: `~/.local/share/ytme/`)
- Mỗi project là 1 folder (user chọn chỗ đặt): `project.json` + `cache/` + `renders/`

---

## 5. Data model — `project.json`

`backend/app/models/` là nguồn sự thật. File `shared/schema/project.schema.json` và type TS đều **sinh tự động** từ đó.

### 5.1 Quy ước đơn vị

| Thứ | Đơn vị |
|---|---|
| Thời gian | **giây, kiểu float** (không dùng ms, không dùng frame) |
| Vị trí element | **tỉ lệ 0–1** của khung hình, lưu **riêng** cho `"16:9"` và `"9:16"` |
| Cỡ chữ / kích thước | **px ở khung tham chiếu 1080p** (tự scale khi output 1440p/4K) |
| Màu | `"#rrggbb"` |
| Âm lượng | LUFS / dB |
| ID | chuỗi ngắn duy nhất (`nanoid` 10 ký tự) |

### 5.2 Ví dụ (rút gọn)

```jsonc
{
  "schemaVersion": 1,
  "name": "Chill Night Mix",
  "library": [
    { "id": "a1", "title": "Midnight Coffee", "source": { "kind": "url", "url": "https://…", "site": "youtube" },
      "cacheWav": "cache/a1.wav", "duration": 222.4, "srcBitrateKbps": 160,
      "loudness": { "i": -9.8, "tp": -0.4, "lra": 6.1 } }
  ],
  "mix": {
    "targetLufs": -14, "autoTrimSilence": true, "fadeInStart": 2, "fadeOutEnd": 5,
    "tracks": [
      { "id": "t1", "libId": "a1", "title": "Midnight Coffee", "trimIn": 2.4, "trimOut": 220.0, "gainDb": 0 }
    ],
    "transitions": {
      "t1>t2": { "presetId": "smooth-blend", "fadeOut": 6, "fadeIn": 6, "overlap": 6,
                 "curveOut": "equal-power", "curveIn": "equal-power", "edited": false }
    }
  },
  "video": {
    "format": "16:9",
    "background": { "fit": "blur", "blur": 30, "dim": 35, "solid": "#14121c" },
    "artwork": { "type": "image", "media": ["media/cover.jpg"], "carousel": { "mode": "song", "everySec": 60 },
                 "scale": 100, "radius": 0, "shadow": true, "border": false,
                 "pos": { "16:9": { "x": 0.5, "y": 0.5 }, "9:16": { "x": 0.5, "y": 0.4 } } },
    "effects": { "zoom": { "on": true, "period": 60 }, "grain": { "on": true, "opacity": 18 } },
    "elements": [
      { "id": "np", "kind": "nowPlaying", "visible": true, "fmt": "{index}. {title}", "label": true,
        "font": "Be Vietnam Pro", "size": 54, "color": "#ffffff", "anim": "fade",
        "pos": { "16:9": { "x": 0.05, "y": 0.80 }, "9:16": { "x": 0.07, "y": 0.82 } } },
      { "id": "title", "kind": "text", "text": "Chill Night Mix", "start": 0, "end": null, "…": "…" },
      { "id": "ov1", "kind": "overlay", "sub": "video", "file": "media/light_leak.mp4",
        "blend": "screen", "opacity": 45, "loopCrossfade": true, "start": 0, "end": null },
      { "id": "viz", "kind": "visualizer", "type": "circular", "style": 0, "size": 26, "…": "…" }
    ]
  },
  "export": { "formats": ["16:9"], "height": 1080, "fps": 30, "quality": "balanced",
              "encoder": "auto", "extras": { "mixMp3": true, "chapters": false } }
}
```

- `elements` có **thứ tự = thứ tự chồng lớp** (phần tử đầu nằm trên cùng), riêng trong nhóm của nó.
- `end: null` nghĩa là "đến hết video".
- Key của transition có dạng `"<idBàiTrước>><idBàiSau>"` (ví dụ `"t1>t2"`) → đổi thứ tự bài thì transition **đi theo cặp bài** (UI-UX §4 ②).
- **Migration:** tăng `schemaVersion` và viết hàm migrate trong `models/migrations.py` cho mọi thay đổi không tương thích. Project cũ **PHẢI** mở được.

### 5.3 Công thức thời gian (PHẢI dùng đúng — `audio/timeline.py`)

```
len[i]      = trimOut[i] - trimIn[i]
start[0]    = 0
start[i+1]  = start[i] + len[i] - overlap[i]          # overlap < 0 → khoảng lặng
total       = start[last] + len[last]
chapter[0]  = 0
chapter[i+1]= start[i+1] + overlap[i]/2   nếu overlap[i] > 0   # giữa vùng crossfade
            = start[i+1]                  nếu overlap[i] ≤ 0   # đầu fade-in
```

`chapter` vừa dùng cho mốc Now Playing, vừa dùng cho `chapters.txt` → hai thứ luôn khớp nhau.

**Validate (F2.12):** `max(fadeOut, fadeIn, overlap) ≤ 0.5 × min(len[i], len[i+1])`.

### 5.4 Gain curve (`audio/curves.py` ↔ `frontend/src/audio/curves.ts`)

`x ∈ [0,1]` là tiến độ fade. `in(x)` là gain fade-in, `out(x) = in(1 − x)`.

| Curve | `in(x)` |
|---|---|
| `equal-power` | `sin(x·π/2)` |
| `linear` | `x` |
| `log` | `x^2.5` — gần tuyến tính theo dB, nghe đều tai nhất khi fade từ / về im lặng |
| `s-curve` | `(1 − cos(π·x)) / 2` |

Fade-out luôn là fade-in **đảo ngược thời gian** — không có công thức fade-out riêng.

Hai bản cài đặt **PHẢI** cho cùng kết quả: test đọc `shared/fixtures/curves.json` (101 điểm mỗi curve) ở cả pytest và Vitest, sai số ≤ 1e-6.

---

## 6. Backend: quy tắc kỹ thuật

### 6.1 API
- REST JSON ở `/api/...`. Router mỏng; logic nằm trong service.
- Tác vụ > 1 giây (tải, decode, normalize, render…) → **luôn là job**: API trả `{ jobId }` ngay, tiến độ đẩy qua WebSocket `/api/ws` với dạng `{ type: "job", id, state, progress, message }`.
- Lỗi trả về `{ code, message_vi, detail }`. `message_vi` là câu tiếng Việt đọc được ("Video riêng tư", "Ổ D: không đủ chỗ"), `detail` dùng để debug.
- Server **PHẢI** bind `127.0.0.1` (N10). Kiểm tra `Host`/`Origin` header để chặn DNS-rebinding.

### 6.2 Gọi FFmpeg / yt-dlp — chỉ qua `core/proc.py`
- **Luôn truyền list argument, KHÔNG BAO GIỜ dùng `shell=True`** và không ghép chuỗi lệnh. Tên file có dấu tiếng Việt, khoảng trắng, `&`… là chuyện bình thường.
- Windows: thêm `creationflags=CREATE_NO_WINDOW` để không nháy cửa sổ console.
- Đọc progress từ FFmpeg bằng `-progress pipe:1 -nostats`; đọc yt-dlp bằng `--newline --progress-template`.
- Mọi process **PHẢI** hủy được (F1.7, F4.5): kill cả cây process khi job bị hủy.
- Log đầy đủ command line + stderr vào file log khi lỗi.

### 6.3 Audio
- **F1.11 — không nén lossy chồng lớp:** ingest decode **một lần** sang `cache/audio/<key>.wav` (**float32, 48 kHz stereo**, RF64 khi > 4 GB — D-23) kèm `<key>.json` ghi thông tin nguồn. Mọi bước sau (cắt, normalize, mix) đọc từ WAV. Chỉ `export.py` được tạo MP3/AAC.
- **Đoạn cắt theo tracklist** không có WAV riêng: item `segment` phát khoảng `start–end` của WAV file gốc (D-26). Đọc audio của một item luôn đi qua `audioOf()` (frontend) / tương đương ở backend.
- **Job không ghi `project.json`** (D-24): job trả kết quả trong event, frontend ghi vào item bằng `patch()` (không tạo bước undo). Đừng thêm code backend sửa project trong lúc frontend đang autosave.
- Cache key = hash của (nội dung file nguồn hoặc URL + format id) + tham số xử lý. Đổi tham số thì cache cũ không được dùng lại.
- **Loudness:** `loudnorm` 2-pass để đo, lưu `{i, tp, lra}` vào project. Áp gain tuyến tính khi mix (không dùng loudnorm động lúc render vì nó làm méo dynamic).
- **Mixer:** stream theo block (ví dụ 1 giây) bằng numpy — không load 3 tiếng vào RAM. Mỗi block: cộng các bài đang phát × gain envelope (từ `curves.py`) → ghi float32 WAV. Sau đó dùng FFmpeg `alimiter` (true-peak −1 dBTP, F2.15) rồi encode.
- **Tracklist:** parser chấp nhận `m:ss`, `mm:ss`, `h:mm:ss`, có/không có dấu `-–—` sau mốc giờ. Dòng lỗi phải báo **số dòng + nội dung**. Mốc phải tăng dần.
- **Spectrum (visualizer):** STFT với hop = `sampleRate / fps`, gom về thang log-frequency (64 bin), smoothing attack/release **tính sẵn trong bước phân tích**. Kết quả là mảng `float16[frames × bins]` lưu `.npy`. Renderer và preview chỉ **tra mảng** theo thời gian, không tự tính.

### 6.4 Video render
- **Mọi effect / overlay / visualizer PHẢI là hàm thuần của thời gian `t`** (và seed). Không được có kiểu `particle.x += vx` qua từng frame. Hạt bụi / tuyết: `pos = fract(seed + velocity·t / loopPeriod)`. Mockup dùng state cho nhanh — **đừng copy cách đó**.
- Effect loop được: chu kỳ của mỗi effect phải là ước số của `loopPeriod` (= chu kỳ Slow Zoom, mặc định 60s; các effect khác mặc định 30s).
- **Shader dùng chung:** file `shared/shaders/*.glsl` **không có dòng `#version`**. Loader tự thêm header:
  - WebGL2: `#version 300 es\nprecision highp float;`
  - moderngl: `#version 330 core`

  Chỉ dùng phần giao nhau của GLSL ES 3.0 và GLSL 330.
- **Readback:** FBO → 2 PBO luân phiên (double-buffer) → pipe vào FFmpeg stdin. **Nên** đổi RGB → NV12 ngay trong shader: lượng dữ liệu qua pipe giảm ~2.7 lần, rất quan trọng ở 4K.
- **Encoder:** dò `h264_nvenc` bằng một lần encode thử 1 giây lúc khởi động. Có thì dùng, không thì `libx264`. Cấu hình (preset, rc, bitrate theo quality × resolution) nằm trong **một** bảng ở `encoder.py`.
- **Chunk (F4.6):** chunk 5 phút, mỗi chunk bắt đầu bằng keyframe, cùng tham số encoder. Trạng thái chunk lưu trong `renders/<jobId>/state.json`. Resume = bỏ qua các chunk đã xong và có hash hợp lệ. Nối bằng concat demuxer (`-c copy`). **Audio mux một lần sau cùng** trên toàn bộ video — không encode audio theo chunk (AAC bị lệch/khựng ở chỗ nối).
- **Overlay video** decode bằng NVDEC (`-hwaccel cuda`) khi có. Ghép ở pass cuối, **không** đưa vào vòng loop nền (F3.58).
- **Text:** vẽ bằng skia-python → texture, cache theo (nội dung, style). Font lấy từ folder font đã bundle — đúng file mà frontend dùng.

### 6.5 File & dữ liệu
- Ghi `project.json` **atomic**: ghi ra `project.json.tmp` → `os.replace`. Giữ 5 bản backup xoay vòng.
- Kiểm tra ổ trống trước khi render (F4.10): `ước tính dung lượng × 1.2 + cache tạm`.
- Dùng `pathlib` ở mọi chỗ. Không hard-code `\` hay `/`.

### 6.6 Code style Python
- `ruff` (line length 100) + `mypy --strict` cho `app/` (test được nới lỏng).
- Type hint đầy đủ. Model dữ liệu dùng pydantic; dataclass chỉ cho struct nội bộ.
- Tên định danh và comment bằng **tiếng Anh**. Chuỗi hiển thị cho user bằng **tiếng Việt**, gom về một chỗ (`app/messages.py`).
- Comment giải thích **vì sao**, không giải thích code đang làm gì.
- Logging bằng module `logging` chuẩn, ghi ra file xoay vòng trong app data. Không dùng `print`.

---

## 7. Frontend: quy tắc kỹ thuật

### 7.1 Cấu trúc
- Chia theo feature (`features/mix/…`), mỗi feature tự chứa component + hook + test của nó.
- Component dùng chung đặt trong `components/` — chỉ chuyển vào đây khi có **≥ 2 nơi dùng**.
- **Mọi chuỗi hiển thị** đặt trong `i18n/vi.json`. Không viết chuỗi tiếng Việt trực tiếp trong JSX.

### 7.2 State
- Zustand store chia slice: `project` (dữ liệu, có undo), `ui` (tab, element đang chọn, zoom), `jobs` (cập nhật từ WebSocket).
- **Undo/Redo (F5.2):** mọi thay đổi trên `project` đi qua `applyChange(recipe)` dùng immer `produceWithPatches` → lưu patches, giữ ≥ 50 bước. Kéo slider liên tục gộp thành **1 bước undo** (commit khi thả chuột).
- **Autosave:** debounce 1 giây → `PUT /api/projects/:id`. Hiện trạng thái "Đang lưu… / ✓ Đã lưu / ⚠ Lỗi lưu" trên top bar.

### 7.3 Preview
- **Transition (F2.8):** gọi `GET /api/mix/transition-snippet?pair=…` → nhận đoạn WAV/Opus đã normalize của 2 bài quanh điểm nối. Áp gain bằng `curves.ts` qua `GainNode.setValueCurveAtTime`. Không tự normalize ở frontend.
- **Video (F3.2):** WebGL2 nạp đúng `shared/shaders`. Thời gian preview lấy từ clock của audio đang phát (`AudioContext.currentTime`), không lấy từ `requestAnimationFrame`. Dữ liệu spectrum tải theo đoạn quanh playhead.
- Máy yếu được phép giảm độ phân giải preview, **không** được đổi công thức vẽ.

### 7.4 Canvas & timeline (F3.38–F3.49)
- Chọn element đồng bộ 3 chiều qua **một** field `ui.selectedId`. Canvas, timeline và Inspector chỉ đọc field đó.
- Hit-test trên canvas dùng bounding box mà renderer trả về sau mỗi lần vẽ. Overlay phủ toàn khung **bỏ qua** khi hit-test.
- Timeline 3 tiếng có thể có hàng trăm block: chỉ render các block nằm trong vùng đang nhìn thấy (virtualize theo trục ngang).

### 7.5 Code style TS
- `strict: true`, không dùng `any` (nếu bắt buộc thì `unknown` + thu hẹp kiểu). ESLint + Prettier mặc định của repo.
- Component là function component; mỗi file một component chính.
- Type dữ liệu project **chỉ import từ type đã sinh** (`src/api/types.gen.ts`). Không định nghĩa lại bằng tay.

---

## 8. Test

### 8.1 Bắt buộc theo loại code

| Loại code | Test bắt buộc | Ví dụ |
|---|---|---|
| Hàm tính toán (curve, timeline, parser, ước tính) | Unit test, gồm các ca biên | overlap âm, bài ngắn hơn transition, tracklist sai định dạng, mốc giờ giảm dần |
| Xử lý audio | Integration test với **file sinh bằng FFmpeg lavfi** | 2 sine 440/660Hz 10s → crossfade 2s → kiểm tra RMS vùng giữa không bị hụt > 1 dB (equal-power) |
| Loudness | Integration | Sine −20 LUFS → normalize → đo lại −14 ± 0.5 |
| Render | **Golden frame test** | Render frame tại t = 0, 12.5, 59.9, 60.0s → so ảnh mẫu (PSNR ≥ 40dB). Frame 0 và frame 60.0 phải gần như trùng (loop liền mạch, F3.26) |
| Chunk / resume | Integration | Render 3 chunk ngắn, kill giữa chunk 2, resume → kết quả = render liền một mạch (cùng hash frame) |
| API | pytest + `httpx.AsyncClient` | Mỗi endpoint: ca đúng + ca lỗi trả `message_vi` |
| Frontend logic | Vitest | store, undo/redo, curves.ts (đọc fixture chung) |
| Luồng chính | Playwright e2e | Tạo project → thêm file → mix → đổi transition → xuất MP3 |

### 8.2 Quy tắc
- **KHÔNG commit nhạc, video hay ảnh có bản quyền vào repo.** Fixture audio/video **sinh ra lúc chạy test** (`ffmpeg -f lavfi -i sine=…`, `testsrc2`, `color=…`). Ảnh mẫu dùng ảnh tự vẽ bằng code.
- Golden image lưu ở `backend/tests/golden/`, cập nhật bằng `pytest --update-golden`, và **phải nêu lý do trong PR**.
- Test chạy được offline. Test cần mạng (yt-dlp) gắn marker `@pytest.mark.network`, mặc định không chạy.
- CI (GitHub Actions) chạy trên **`windows-latest`** và `ubuntu-latest`: lint, typecheck, unit test, integration test (FFmpeg có sẵn trên runner). Test cần GPU / NVENC gắn marker `gpu`, Product Owner chạy tay trên máy thật.

---

## 9. Milestone & task

Ước lượng cho **1 developer full-time, có kinh nghiệm Python + React**, chưa tính thời gian chờ review. Tổng **~11–14 tuần**. Đây là ước lượng — QA sẽ cập nhật sau M0 và M1.

### M0 — Spike S1: benchmark render · *3–5 ngày* · **LÀM TRƯỚC TIÊN**
**Mục tiêu:** trả lời "render có đủ nhanh trên RTX 3050 6GB không" và chọn kiến trúc render trước khi viết UI.
- `bench/run_bench.py` + `bench/README.md`: một lệnh chạy được trên Windows, tự sinh dữ liệu (ảnh gradient, audio sine 10 phút, overlay video từ `testsrc2`). **Không cần file nào của user.**
- Đo 2 chiến lược:
  - **A** — vẽ mọi thứ ở từng frame.
  - **B** — render vòng loop nền 60s một lần rồi decode lặp lại + ghép overlay/viz/text.
- Ma trận: {1080p, 1440p, 2160p} × {A, B} × {không overlay, 1 overlay video} × {NVENC, x264}. Kịch bản: zoom + grain + dust + circular visualizer + 2 text.
- In bảng: fps render, **× realtime**, % GPU / CPU, VRAM, dung lượng file. Lưu `bench/results-<máy>.json`.
- **Xong khi:** Product Owner chạy trên máy thật, kết quả được ghi vào `DECISIONS.md`, N3 trong `REQUIREMENTS.md` được cập nhật bằng số thật.

### M1 — Skeleton · *~1 tuần*
- Khung backend (FastAPI, config, `proc.py`, job queue + WebSocket, logging), khung frontend (4 tab, top bar, token, i18n), proxy dev.
- Model pydantic v1 → sinh schema → sinh TS type (có lệnh `gen:types`).
- Project: tạo / mở / lưu atomic / autosave / gần đây (F5.1, F5.2 phần autosave, F5.4).
- Dò FFmpeg / NVENC / yt-dlp ở `GET /api/system` và hiện trong Settings.
- CI workflow, PR template, `Start.bat` chạy được bản dev.
- **Xong khi:** CI xanh trên Windows; mở app → tạo project → đóng → mở lại vẫn còn.

### M2 — Thư viện · *~1.5 tuần* · F1.1–F1.11
- Ingest file / folder, probe, decode WAV cache. (Peaks chuyển sang M3 — D-31.)
- yt-dlp: link đơn, playlist (modal tick chọn), tiến độ, hủy, lỗi tiếng Việt, cập nhật yt-dlp.
- Cắt theo tracklist → thêm vào Mix; xuất MP3 320 CBR hàng loạt theo pattern tên.
- **Xong khi:** acceptance 1 và 2 ở `REQUIREMENTS.md` §8 đạt.

### M3 — Mix · *~2 tuần* · F2.1–F2.22
- Danh sách kéo thả, overview, chip transition, Transition Editor (biểu đồ + kéo handle + ô số), 5 preset + lưu/sửa/xóa preset, áp dụng hàng loạt, validate.
- Loudness 2-pass, auto trim, trim tay, nghe thử transition (Web Audio), mixer streaming + limiter, xuất mix MP3, chapters + validate theo luật YouTube.
- **Xong khi:** acceptance 3 và 4 đạt; mix 40 bài xuất ≤ 5 phút (N4).

### M4 — Video core · *~3 tuần* · F3.1–F3.9, F3.27–F3.49
- Engine shader dùng chung (loader WebGL2 + moderngl), scene model, artwork / nền / fit mode, carousel, video loop.
- 9 style visualizer từ spectrum precompute; Now Playing, text, logo (skia → texture).
- Canvas preview, timeline layer (zoom, virtualize, kéo thanh, mắt ẩn/hiện, xem chỗ nối loop), Inspector, chọn đồng bộ 3 chiều, vị trí riêng 16:9 / 9:16.
- **Xong khi:** golden frame test đạt; preview và render cùng frame lệch ≤ ngưỡng (N6).

### M5 — Effect & Overlay · *~1.5 tuần* · F3.10–F3.15, F3.21–F3.26, F3.52–F3.58
- 6 effect P1 (thuần `f(t)`, loop được), cảnh báo > 3 effect, preset style A–F, lưu preset style.
- Overlay video (loop + crossfade, alpha, NVDEC), overlay PNG, màu / gradient / vignette, 6 blend mode.
- **Xong khi:** acceptance overlay đạt; frame 0 và frame `loopPeriod` khớp nhau.

### M6 — Xuất · *~1.5 tuần* · F4.1–F4.10
- Cài đặt output, dò encoder, ước tính (dựa trên lần render thử gần nhất), render thử 30s, hàng đợi, chunk + resume, concat + mux audio, kiểm tra ổ trống, mở folder.
- **Xong khi:** acceptance render và resume đạt trên máy Product Owner.

### M7 — Hoàn thiện · *~1 tuần*
- Bản portable Windows (Python embedded + FFmpeg + yt-dlp + font + frontend build), dọn cache, xử lý lỗi, chạy lại toàn bộ acceptance §8 trên máy thật.

> **Quy tắc thứ tự:** M0 → M1 bắt buộc theo thứ tự. M2 và M3 làm nối tiếp được. **Không bắt đầu M4 khi M0 chưa có kết luận.**

---

## 10. Quy trình làm việc, PR & QA

### 10.1 Branch & commit
- `main` được bảo vệ; chỉ merge qua PR, Product Owner bấm merge.
- Branch: `feat/m3-transition-editor`, `fix/m2-ytdlp-progress`, `chore/ci-windows`.
- Commit theo [Conventional Commits](https://www.conventionalcommits.org/): `feat(mix): add equal-power crossfade`.
- PR **nhỏ**: *nên* < 500 dòng thay đổi (không tính file sinh tự động). Một PR làm một việc.

### 10.2 Mở PR
Dùng template `.github/pull_request_template.md`. **PHẢI** có:
1. **Requirement ID** đã làm (đủ hay một phần).
2. **Cách đã test**: lệnh đã chạy, kết quả, máy/OS.
3. **Ảnh chụp hoặc GIF** nếu có thay đổi UI. Đặt cạnh mockup tương ứng để so.
4. Chỗ nào **lệch khỏi spec** và lý do.

### 10.3 QA (Claude) review cái gì

| Hạng mục | Kiểm tra |
|---|---|
| Đúng requirement | Đối chiếu từng ID trong PR với `REQUIREMENTS.md` và `UI-UX.md` |
| Test | Chạy lint, typecheck, test. Test có bao các ca biên không, có test thật sự kiểm chứng hành vi hay chỉ cho có |
| Quy tắc cứng | Không `shell=True`; không nén lossy chồng lớp; effect thuần `f(t)`; chuỗi UI nằm trong i18n; không commit media có bản quyền; bind `127.0.0.1` |
| Windows | Đường dẫn có dấu tiếng Việt + khoảng trắng; hủy job kill hết process con; không nháy console |
| Hiệu năng | Không load cả file 3 tiếng vào RAM; timeline không lag với 100 bài (N5) |
| Code | Đơn giản, đúng chỗ theo §3, không thừa dependency, không code chết |

Kết quả review: **Approve** (đủ điều kiện để Product Owner merge) hoặc **Request changes** kèm danh sách lỗi theo mức độ, mỗi lỗi chỉ rõ file:dòng + cách tái hiện.

### 10.4 Hỏi khi chưa rõ
- Requirement mơ hồ hoặc mâu thuẫn → comment vào issue / PR, tag Product Owner. **Không tự đoán rồi làm.**
- Quyết định kỹ thuật có ảnh hưởng lâu dài (đổi thư viện, đổi format file, đổi kiến trúc) → thêm một mục vào `docs/DECISIONS.md` trong cùng PR.
- Muốn thêm tính năng ngoài P1 → đề xuất trong issue, **không** gộp vào PR đang làm.

---

## 11. Definition of Done

Một task chỉ được coi là **xong** khi đủ tất cả:

- [ ] Làm đủ requirement ID đã nhận (hoặc ghi rõ phần chưa làm + lý do)
- [ ] Có test theo §8.1; CI xanh trên `windows-latest`
- [ ] `ruff`, `mypy`, ESLint, `tsc` không lỗi
- [ ] Chuỗi UI nằm trong `vi.json`, lỗi hiện bằng tiếng Việt dễ hiểu
- [ ] UI khớp mockup / spec (có ảnh chụp trong PR)
- [ ] Đã thử với đường dẫn chứa dấu tiếng Việt + khoảng trắng
- [ ] Tác vụ dài: có tiến độ, hủy được, không khóa UI
- [ ] Đổi schema → có migration + đã sinh lại type
- [ ] Cập nhật tài liệu nếu hành vi khác spec (`REQUIREMENTS.md` / `UI-UX.md` / `DECISIONS.md`)
- [ ] QA approve

---

## 12. Những lỗi hay gặp — đừng mắc

| Lỗi | Hậu quả | Làm đúng |
|---|---|---|
| Cắt → xuất MP3 → mix lại từ MP3 | Nén lossy 2–3 lần, nghe tệ dần | Luôn đọc từ WAV cache (F1.11) |
| Particle cập nhật vị trí theo frame | Resume / chunk / preview ra hình khác nhau | `pos = f(seed, t)` |
| Crossfade bằng curve linear | Hụt âm lượng ~3 dB ở giữa | Mặc định equal-power |
| Encode audio theo từng chunk rồi nối | Click / khựng ở chỗ nối chunk | Mux audio 1 lần sau cùng |
| `subprocess.run(f"ffmpeg -i {path} …", shell=True)` | Hỏng khi tên file có dấu / khoảng trắng; lỗ hổng injection | List argument qua `core/proc.py` |
| Load audio 3 tiếng vào numpy một lần | ~4 GB RAM (float32 stereo 48 kHz) | Stream theo block |
| Đọc pixel bằng `glReadPixels` đồng bộ | GPU đứng chờ, render chậm 2–3 lần | Double-buffer PBO |
| Lấy thời gian preview từ `requestAnimationFrame` | Hình lệch khỏi tiếng | Lấy từ `AudioContext.currentTime` |
| Load font từ Google Fonts | App offline bị lỗi chữ | Bundle font local, dùng chung cho preview & render |
| Commit file nhạc / footage để test | Rủi ro bản quyền, repo phình to | Sinh fixture bằng FFmpeg lavfi |
