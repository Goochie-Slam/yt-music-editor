# YT Music Editor — Requirements v0.1

> Trạng thái: **Draft — chờ anh review**
> Ngày: 2026-10-12
> Tài liệu liên quan: [`UI-UX.md`](./UI-UX.md) · [`ui-mockup.html`](./ui-mockup.html) · [`visual-effects-reference.md`](./visual-effects-reference.md)

---

## 0. Tóm tắt

Ứng dụng **chạy local trên Windows** (giao diện mở trong trình duyệt) để sản xuất video playlist nhạc dài 1–3 tiếng:

1. **Lấy audio** từ file local (mọi định dạng FFmpeg đọc được) hoặc từ link (YouTube, SoundCloud, Mixcloud…), tách/cắt theo danh sách user chọn.
2. **Xuất hàng loạt MP3** 320kbps.
3. **Ghép mix** bằng danh sách kéo thả, transition fade/crossfade chỉnh riêng từng điểm nối, có preset.
4. **Render MP4** từ ảnh / carousel / video nền + effect + sóng nhạc + tên bài, xuất 16:9 hoặc 9:16.

Người dùng: 1 người, dùng local, không có tài khoản, không có cloud.

---

## 1. Quyết định đã chốt

| # | Chủ đề | Quyết định |
|---|---|---|
| 1 | Kiểu transition | Hỗ trợ cả **crossfade (chồng)** và **fade out → fade in (không chồng / có khoảng lặng)** |
| 2 | Độ dài transition | Chỉnh riêng từng điểm nối + lưu preset. Có sẵn **5 preset** |
| 3 | Đường cong fade | Em quyết: mặc định **Equal-power**; có thêm Linear, Log, S-curve trong phần nâng cao |
| 4 | Cân bằng âm lượng | Có — normalize từng bài về **-14 LUFS**, true-peak ≤ -1 dBTP |
| 5 | Cắt đầu/cuối bài | Có — tự động cắt khoảng lặng + chỉnh tay |
| 6 | Beat-match / DJ | **Không** |
| 7 | Nguồn audio | **File local + link** (YouTube, SoundCloud, Mixcloud, …) |
| 8 | MP3 | 320kbps CBR, **không** ghi/sửa tag |
| 9 | Nền video | Ảnh tĩnh, carousel, video loop — chọn theo từng sản phẩm |
| 10 | Khung hình | 16:9 (chính) và 9:16. Nguồn lệch tỉ lệ → **blur fill** hoặc **solid color** (user chọn) |
| 11 | Effect | Theo `visual-effects-reference.md` |
| 12 | Sóng nhạc | 3 loại (Bars, Waveform, Circular) × 3 style = **9 style** |
| 13 | Tên bài + timestamp | Có, **optional** (bật/tắt riêng) |
| 14 | Độ dài | Mix 1–3 tiếng |
| 15–17 | Nền tảng | Local only · Windows · Web app local (Python + FFmpeg backend, UI trên trình duyệt) |

---

## 2. Giả định cần anh xác nhận

| ID | Giả định của em | Nếu sai thì sao |
|---|---|---|
| A1 | "Tách theo list" gồm **2 việc**: (a) chuyển nhiều file/link sang MP3, (b) **cắt 1 file dài thành nhiều bài theo tracklist** (dán `00:00 Bài A`…) | Nếu không cần (b) thì bỏ module cắt tracklist, tiết kiệm công |
| A2 | Link playlist (YouTube playlist, SoundCloud set) → app liệt kê bài, user tick chọn bài cần lấy | — |
| A3 | Tên bài hiển thị lấy từ **tên file / tiêu đề link**, user sửa được **trong app** (không ghi vào tag MP3) | — |
| A4 | Output video: **1080p**, 30fps mặc định (có 60fps); 4K để Phase 3 | 4K render chậm ~4 lần, file nặng ~3–4 lần |
| A5 | Máy anh có **GPU rời** (NVIDIA / AMD) hoặc Intel iGPU đời mới | Không có GPU thì render 3 tiếng có thể mất **vài tiếng** — xem R2 |
| A6 | UI tiếng Việt, hỗ trợ font có dấu tiếng Việt cho chữ trên video | — |

---

## 3. Functional Requirements

Ưu tiên: **P1** = MVP · **P2** = bản tiếp theo · **P3** = sau / tùy nhu cầu.

### M1. Thư viện & Lấy audio

| ID | Requirement | Ưu tiên |
|---|---|---|
| F1.1 | Kéo thả nhiều file/folder vào app. Hỗ trợ mọi định dạng FFmpeg decode được: `mp4 mkv mov avi webm flv wmv mp3 wav flac m4a aac ogg opus wma aiff` | P1 |
| F1.2 | Dán **1 hoặc nhiều link** (mỗi dòng 1 link): YouTube, SoundCloud, Mixcloud và các site [yt-dlp hỗ trợ](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md). Link playlist → hiện danh sách bài để tick chọn | P1 |
| F1.3 | Mỗi item hiển thị: tên, nguồn, định dạng, thời lượng, bitrate nguồn, trạng thái (đang tải / đang xử lý / xong / lỗi + lý do) | P1 |
| F1.4 | Tick chọn item → **Xuất MP3 320kbps CBR** hàng loạt vào folder chọn. Pattern tên file: `{index} - {title}.mp3` (sửa được) | P1 |
| F1.5 | **Cắt theo tracklist:** chọn 1 file dài + dán tracklist dạng `mm:ss Tên` hoặc `hh:mm:ss Tên` → preview danh sách đoạn → xuất mỗi đoạn 1 MP3 | P1 |
| F1.6 | Nút "Thêm vào Mix" cho item đã chọn | P1 |
| F1.7 | Chạy song song tối đa N tác vụ (mặc định 3), có hủy | P1 |
| F1.8 | Cảnh báo khi bitrate nguồn thấp (ví dụ YouTube ~128–160kbps): *"Xuất 320kbps không làm chất lượng tốt hơn nguồn"* | P1 |
| F1.9 | Nút **cập nhật yt-dlp** trong Settings (YouTube đổi hệ thống liên tục, yt-dlp cũ sẽ hỏng) | P1 |
| F1.10 | Cache: file đã tải/đã decode không xử lý lại | P1 |

**Ngoài phạm vi:** vượt DRM, tải nội dung trả phí, đăng nhập tài khoản nền tảng.

### M2. Mix & Transition

#### 2.1 Danh sách mix

| ID | Requirement | Ưu tiên |
|---|---|---|
| F2.1 | Danh sách bài **dọc**, kéo thả để đổi thứ tự (drag handle), xóa, nhân bản | P1 |
| F2.2 | Mỗi bài: số thứ tự, tên hiển thị (sửa được), thời lượng sau trim, mini waveform | P1 |
| F2.3 | Thanh **Overview** phía trên thể hiện cả mix theo tỉ lệ thời gian: block bài, vùng transition, mốc timestamp. Click → nhảy tới bài | P1 |
| F2.4 | Footer: tổng số bài, tổng thời lượng (đã tính overlap), dung lượng ước tính | P1 |
| F2.5 | Shuffle, sắp theo tên (tiện ích) | P3 |

#### 2.2 Mô hình transition

Mỗi điểm nối giữa bài *N* và *N+1* có **1 transition** gồm:

| Tham số | Ý nghĩa | Phạm vi |
|---|---|---|
| `fadeOut` | Thời gian bài trước nhỏ dần về 0 | 0 – 20s |
| `fadeIn` | Thời gian bài sau to dần từ 0 | 0 – 20s |
| `overlap` | Số giây 2 bài **chồng lên nhau**. `> 0` = crossfade, `= 0` = nối liền, `< 0` = **khoảng lặng** | -5 – 20s |
| `curveOut`, `curveIn` | Equal-power · Linear · Log · S-curve | — |

> Một mô hình duy nhất cho cả 2 kiểu: **crossfade** là `overlap > 0`, **fade out → fade in** là `overlap ≤ 0`. Không cần 2 code path.

```
overlap > 0 (crossfade)              overlap < 0 (fade → lặng → fade)
Bài N   ███████▓▓▒▒░░                Bài N   ███████▓▓▒░
Bài N+1        ░░▒▒▓▓███████         Bài N+1             ░▒▓▓███████
               |overlap|                        |gap|
```

| ID | Requirement | Ưu tiên |
|---|---|---|
| F2.6 | Giữa 2 bài trong danh sách có **chip transition** hiển thị tên preset + thời lượng. Click → mở Transition Editor | P1 |
| F2.7 | Transition Editor: biểu đồ 2 waveform chồng nhau + đường cong fade, **kéo handle** để chỉnh `fadeOut`/`fadeIn`/`overlap`, kèm ô số chính xác | P1 |
| F2.8 | Nút **Nghe thử**: phát đoạn ~8s trước → ~8s sau điểm nối, phát ngay trong trình duyệt (Web Audio), không cần render | P1 |
| F2.9 | Chọn preset từ dropdown. Sửa tham số → chip hiện "*Preset (đã chỉnh)*" | P1 |
| F2.10 | **Lưu thành preset** (đặt tên), sửa / xóa preset của user. Preset mặc định không xóa được | P1 |
| F2.11 | "Áp dụng cho tất cả điểm nối" và "Áp dụng cho các điểm nối đã chọn" | P1 |
| F2.12 | Validate: `fadeOut`, `fadeIn`, `overlap` không vượt quá 50% thời lượng của bài ngắn hơn. Báo lỗi ngay trên chip | P1 |
| F2.13 | Fade-in đầu mix và fade-out cuối mix (cấu hình riêng, mặc định 2s / 5s) | P1 |

#### 2.3 Năm preset mặc định

| # | Tên | fadeOut | fadeIn | overlap | Curve | Dùng khi |
|---|---|---|---|---|---|---|
| 1 | **Smooth Blend** *(mặc định)* | 6s | 6s | 6s | Equal-power | R&B, ballad, phần lớn playlist |
| 2 | **Quick Mix** | 2.5s | 2.5s | 2.5s | Equal-power | EDM, remix, disco — giữ năng lượng, không bị hụt |
| 3 | **Long Dissolve** | 12s | 12s | 12s | S-curve | Lofi, sleep, ambient, piano — tan vào nhau rất chậm |
| 4 | **Radio Segue** | 5s | 1.5s | 1.5s | Out: Log · In: Equal-power | Pop, bài có intro mạnh — bài trước rút dài, bài sau vào nhanh và rõ |
| 5 | **Fade & Breathe** | 3s | 1s | **-1.5s** (lặng 1.5s) | Out: Log · In: Linear | Jazz, acoustic, đổi mood — tách bạch từng bài |

*Vì sao Equal-power:* khi 2 bài chồng nhau, Linear tạo "hố" âm lượng ở giữa (~-3dB). Equal-power giữ cảm giác âm lượng ổn định. Log hợp cho fade-out không chồng vì tai nghe theo thang dB.

#### 2.4 Âm lượng & trim

| ID | Requirement | Ưu tiên |
|---|---|---|
| F2.14 | Normalize từng bài về target LUFS (mặc định **-14**, chọn được -16 / -12). Đo 2-pass (`loudnorm`), cache kết quả | P1 |
| F2.15 | Limiter cuối mix (true-peak -1 dBTP) chống clip ở vùng crossfade | P1 |
| F2.16 | Hiển thị LUFS gốc từng bài; badge cảnh báo khi bài lệch > 6 LU so với target (thường là nguồn kém) | P2 |
| F2.17 | **Auto trim** khoảng lặng đầu/cuối (ngưỡng mặc định -50 dBFS, ≥ 0.5s) — bật/tắt toàn mix | P1 |
| F2.18 | Trim tay: kéo handle in/out trên waveform của từng bài, có nghe thử điểm cắt | P1 |
| F2.19 | Chỉnh gain riêng từng bài (±6 dB) sau normalize | P2 |

#### 2.5 Xuất mix

| ID | Requirement | Ưu tiên |
|---|---|---|
| F2.20 | Xuất **1 file MP3 320kbps** cho cả mix | P1 |
| F2.21 | Xuất **timestamp/chapters** `.txt` (optional): `00:00 Tên bài`. Mốc = điểm giữa vùng crossfade, hoặc đầu fade-in nếu có khoảng lặng | P1 |
| F2.22 | Validate chapters theo luật YouTube: mốc đầu `00:00`, ≥ 3 mốc, mỗi đoạn ≥ 10s → cảnh báo nếu vi phạm | P1 |

### M3. Video

#### 3.1 Canvas & khung hình

| ID | Requirement | Ưu tiên |
|---|---|---|
| F3.1 | Chọn khung hình **16:9 (1920×1080)** hoặc **9:16 (1080×1920)**. Cùng project có thể xuất cả hai | P1 |
| F3.2 | Preview trực tiếp trên canvas, phát đồng bộ với audio mix, tua được | P1 |
| F3.3 | Hiện **safe area** (vùng UI YouTube / Shorts che) bật/tắt được | P2 |

#### 3.2 Nền (Background)

| ID | Requirement | Ưu tiên |
|---|---|---|
| F3.4 | **Ảnh tĩnh**: 1 ảnh | P1 |
| F3.5 | **Carousel**: nhiều ảnh, đổi theo (a) mỗi X giây, hoặc (b) **theo bài** (đổi ảnh lúc đổi bài). Chuyển ảnh crossfade 1–3s | P1 |
| F3.6 | **Video loop**: 1 video lặp suốt mix. Tùy chọn crossfade ở điểm loop (0.5–2s) để giấu chỗ nối | P1 |
| F3.7 | **Fit mode** khi nguồn khác tỉ lệ output: `Blur fill` (nền = chính ảnh đó phóng to + blur + tối đi) · `Solid color` (chọn màu) · `Crop fill` (phóng to cắt cho đầy) | P1 |
| F3.8 | Fit mode áp dụng cho cả ảnh, từng ảnh carousel và video | P1 |
| F3.9 | Chỉnh độ blur (0–60) và độ tối (0–80%) cho Blur fill | P1 |

#### 3.3 Effect

Theo `visual-effects-reference.md`. Mọi effect render **procedural** (tự sinh bằng shader), không cần stock footage — trừ Custom Overlay.

| ID | Effect | Tham số chính | Ưu tiên |
|---|---|---|---|
| F3.10 | Slow Zoom / Ken Burns | zoom 100→105–110%, chu kỳ 30–120s, hướng pan, ping-pong loop | P1 |
| F3.11 | Film Grain | opacity 0–40%, kích thước hạt | P1 |
| F3.12 | Glow / Bloom | ngưỡng sáng, độ mạnh, bán kính | P1 |
| F3.13 | Floating Dust / Particles | mật độ, kích thước, tốc độ, hướng | P1 |
| F3.14 | Snowfall | mật độ, kích thước, tốc độ, độ sâu (3 lớp) | P1 |
| F3.15 | Bokeh / Light Leak | số orb, màu, opacity 0–30%, tốc độ trôi | P1 |
| F3.16 | VHS / Chromatic Aberration | độ lệch RGB, scanline, noise, tần suất glitch nhẹ | P2 |
| F3.17 | Fog / Smoke | mật độ, tốc độ, màu | P2 |
| F3.18 | Rain (procedural, rơi ngoài trời) | mật độ, góc, tốc độ | P2 |
| F3.19 | **Custom Overlay**: user đưa video overlay (mưa trên kính, khói, light leak) + blend mode Screen / Add / Overlay + opacity | — | P2 |
| F3.20 | Parallax / 2.5D | cần AI tách lớp depth + inpaint | **P3** — xem R5 |

| ID | Requirement | Ưu tiên |
|---|---|---|
| F3.21 | Bật/tắt từng effect, sắp thứ tự layer | P1 |
| F3.22 | **Cảnh báo khi bật > 3 effect** (theo guideline: chọn 2–3 effect) | P1 |
| F3.23 | **Preset effect A–F** theo guideline: Late-Night R&B, Bossa Nova Café, Party Remix, Christmas, Lofi/Sad, Synthwave. Preset dùng effect P2 thì hiện "sắp có" | P1 |
| F3.24 | Lưu preset effect của user (gồm effect + visualizer + text style) | P1 |
| F3.25 | Tùy chọn "phản ứng theo bass" cho Glow và Zoom (dùng dữ liệu audio thật) | P2 |
| F3.26 | Mọi effect với nền ảnh tĩnh phải **loop liền mạch**, không có cú giật khi reset | P1 |

#### 3.4 Sóng nhạc (Visualizer)

Bắt buộc **audio-reactive thật** (FFT từ audio mix), không phải animation giả.

| Loại | Style 1 | Style 2 | Style 3 |
|---|---|---|---|
| **Bars** | Classic — cột dọc mọc từ đáy | Mirrored — đối xứng trên/dưới quanh trục giữa | Capsule — cột bo tròn + "peak cap" rơi chậm |
| **Waveform** | Line — đường sóng mảnh | Filled — sóng đặc, đối xứng | Neon Layers — 3 đường lệch pha, glow mờ dần |
| **Circular** | Radial Bars — cột tỏa quanh vòng tròn (giữa đặt logo/ảnh) | Ring Wave — vòng sóng khép kín | Dot Ring — chấm tròn nhảy theo nhịp |

| ID | Requirement | Ưu tiên |
|---|---|---|
| F3.27 | 9 style như bảng trên | P1 |
| F3.28 | Tham số chung: màu / gradient, opacity, kích thước, vị trí (kéo trên canvas + 9 điểm neo), độ nhạy, độ mượt, số cột, dải tần | P1 |
| F3.29 | Mặc định **nhỏ, đặt xa tiêu đề** (theo guideline). Cảnh báo khi visualizer chiếm > 35% chiều rộng | P2 |
| F3.30 | Ảnh ở giữa Circular: upload riêng hoặc dùng ảnh nền crop tròn | P1 |
| F3.31 | Tắt hẳn visualizer được | P1 |

#### 3.5 Element chữ & hình

| ID | Requirement | Ưu tiên |
|---|---|---|
| F3.32 | **Now Playing** (optional): tên bài đang phát, tự đổi khi đổi bài, animation vào/ra (fade / slide), format `{title}` hoặc `{index}. {title}` | P1 |
| F3.33 | **Tiêu đề playlist** tĩnh (optional) | P1 |
| F3.34 | **Logo / watermark** (PNG trong suốt), vị trí + opacity | P1 |
| F3.35 | Thanh **progress** của bài hiện tại (optional) | P2 |
| F3.36 | Text style: font (có sẵn ≥ 6 font hỗ trợ tiếng Việt + font hệ thống), cỡ, màu, shadow, outline, letter-spacing | P1 |
| F3.37 | Kéo thả vị trí element trên canvas, snap theo lưới / safe area | P1 |

### M4. Xuất & Render

| ID | Requirement | Ưu tiên |
|---|---|---|
| F4.1 | Cài đặt output: khung hình (16:9 / 9:16 / cả hai), 1080p, 30/60fps, chất lượng (Nhẹ / Cân bằng / Cao) | P1 |
| F4.2 | Encoder: **tự phát hiện** GPU encoder (NVENC / AMF / QSV), fallback CPU (x264). H.264 + AAC 320kbps | P1 |
| F4.3 | **Render thử 30 giây** ở vị trí bất kỳ → xem kết quả thật trước khi render dài | P1 |
| F4.4 | Ước tính trước khi render: dung lượng file, thời gian render (từ benchmark render thử) | P1 |
| F4.5 | **Hàng đợi render**: nhiều job, progress %, ETA, hủy, mở folder output | P1 |
| F4.6 | Render **theo chunk** (ví dụ 5 phút/chunk) → crash / tắt máy giữa chừng thì **resume** từ chunk cuối, không làm lại từ đầu | P1 |
| F4.7 | Job vẫn chạy khi đóng tab trình duyệt; mở lại thấy tiến độ | P1 |
| F4.8 | Output đi kèm (tick chọn): `video.mp4`, `mix.mp3`, `chapters.txt` | P1 |
| F4.9 | Thông báo Windows khi render xong | P2 |
| F4.10 | Kiểm tra dung lượng ổ trống trước khi render, chặn nếu không đủ | P1 |

### M5. Project & Preset

| ID | Requirement | Ưu tiên |
|---|---|---|
| F5.1 | Project = 1 folder chứa `project.json` + cache. Tạo / mở / lưu / nhân bản project | P1 |
| F5.2 | **Autosave** mỗi thay đổi; Undo / Redo (≥ 50 bước) trong Mix và Video | P1 |
| F5.3 | Preset (transition, effect, visualizer, text) lưu global, dùng chung mọi project. Export / import preset `.json` | P1 |
| F5.4 | Màn hình Home: danh sách project gần đây + thumbnail | P1 |
| F5.5 | **Template project**: lưu toàn bộ setting video (không gồm bài) để làm series cùng phong cách | P2 |

---

## 4. Non-functional Requirements

| ID | Requirement | Mục tiêu |
|---|---|---|
| N1 | Hệ điều hành | Windows 10/11 64-bit. Bản portable: giải nén → chạy `Start.bat` → tự mở trình duyệt. Đã bundle Python, FFmpeg, yt-dlp |
| N2 | Offline | Mọi chức năng trừ tải link đều chạy offline |
| N3 | **Tốc độ render** (1080p30, nền ảnh + 2–3 effect + visualizer) | Có GPU: **≥ 2× realtime** (mix 3 tiếng ≤ 90 phút). Chỉ CPU: ≥ 0.7× realtime. *Con số sẽ được đo ở Spike S1 rồi chốt lại* |
| N4 | Xuất mix MP3 3 tiếng (đã có cache normalize) | ≤ 5 phút |
| N5 | UI mượt với 100 bài trong mix | Kéo thả không lag, mở Transition Editor < 300ms |
| N6 | Preview ↔ render | Preview trên canvas **giống bản render** (cùng shader). Sai khác chấp nhận: chất lượng preview thấp hơn khi máy yếu |
| N7 | Ổn định | Render 3 tiếng không rò bộ nhớ. RAM backend < 4GB |
| N8 | Dung lượng tạm | Cache audio ~2GB / 3 tiếng (WAV). Hiện dung lượng cache, có nút dọn |
| N9 | Font | Chữ tiếng Việt có dấu hiển thị đúng trên preview **và** video render |
| N10 | Bảo mật local | Server chỉ bind `127.0.0.1`, không mở ra mạng LAN |

---

## 5. Kiến trúc đề xuất

```
┌──────────── Trình duyệt (localhost) ────────────┐
│ React + TypeScript + Vite                       │
│  • dnd-kit (kéo thả)  • Waveform từ peaks JSON  │
│  • Web Audio API (nghe thử transition)          │
│  • WebGL preview (dùng CHUNG shader GLSL)       │
└───────────────▲─────────────────────────────────┘
                │ REST + WebSocket (progress)
┌───────────────┴─────────────────────────────────┐
│ Python 3.12 · FastAPI · job queue (process pool)│
│  • yt-dlp           → tải link                   │
│  • FFmpeg/ffprobe   → decode, loudnorm, fade,   │
│                       mix, encode (NVENC/AMF/QSV)│
│  • numpy            → peaks, FFT theo từng frame │
│  • moderngl (GLSL)  → render effect + visualizer │
│  • project.json + cache folder                   │
└──────────────────────────────────────────────────┘
```

**Pipeline render video:**

1. **Audio master:** normalize từng bài (cache) → trim → fade/overlap theo transition → limiter → `mix.wav`.
2. **Phân tích audio:** FFT cho mọi frame (numpy, vector hóa) → mảng dữ liệu cho visualizer.
3. **Background loop:** với nền ảnh tĩnh, mọi effect thiết kế **tuần hoàn** (chu kỳ 30–60s) → render **1 vòng loop duy nhất**, sau đó lặp. Thời gian render nền không phụ thuộc độ dài mix.
4. **Overlay pass:** visualizer + text render theo từng frame trên toàn thời lượng, composite lên nền đã loop.
5. **Encode theo chunk** bằng GPU encoder → nối chunk (concat, không re-encode) → ghép audio AAC.

> Lưu ý: tối ưu ở bước 3 **chỉ áp dụng cho nền ảnh tĩnh**. Carousel và video nền phải render effect trên toàn thời lượng → chậm hơn đáng kể.

---

## 6. Rủi ro (nói thẳng)

| ID | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | **Bản quyền / Content ID.** Video mix nhạc người khác đăng YouTube rất dễ bị claim, mất kiếm tiền, bị strike. Tải từ YouTube/SoundCloud/Mixcloud vi phạm ToS của các nền tảng đó. Tool không giải quyết được chuyện này | **Cao** (với kênh) | Ngoài phạm vi kỹ thuật. Anh cần chiến lược nguồn nhạc riêng (nhạc có license, royalty-free, nhạc tự sản xuất / AI có quyền thương mại) |
| R2 | **Render chậm.** 3 tiếng × 30fps = 324.000 frame. Máy không có GPU tốt có thể render mất vài tiếng | Cao | Loop nền (mục 5.3), GPU encode, chunk + resume, render thử 30s để đo. **Spike S1 làm đầu tiên** |
| R3 | **yt-dlp hỏng** khi YouTube đổi hệ thống (vài lần/năm) | Trung bình | Nút cập nhật yt-dlp; tải link tách hẳn khỏi phần còn lại |
| R4 | **Chất lượng nguồn từ link** ~128–160kbps. Đổi sang MP3 320kbps chỉ làm file nặng hơn, **không** hay hơn | Trung bình | Cảnh báo F1.8. Ưu tiên file gốc chất lượng cao khi có |
| R5 | **Parallax 2.5D** cần model AI tách depth + inpaint. Kết quả hay lỗi méo mặt / viền cắt — đúng thứ guideline bảo tránh | Cao | Đẩy xuống P3, chỉ làm nếu thật sự cần |
| R6 | **Grain / mưa / bụi làm file phình to.** Noise khó nén → 3 tiếng 1080p có thể **10–16GB**, và YouTube nén lại thì grain cũng nát | Trung bình | Hiện ước tính dung lượng; preset quality; khuyến nghị grain ≤ 15% |
| R7 | **Preview khác bản render** | Trung bình | Dùng chung shader GLSL cho WebGL preview và moderngl render; có render thử 30s |
| R8 | **Phình phạm vi.** 4 module + 9 visualizer + 11 effect + preset là khối lượng lớn | **Cao** | Bám roadmap. Chưa xong P1 thì không làm P2 |

---

## 7. Roadmap

| Giai đoạn | Nội dung | Kết quả |
|---|---|---|
| **Spike S1** | Benchmark render 10 phút 1080p (ảnh + zoom + grain + bars) với moderngl + NVENC/x264 trên Windows | Chốt kiến trúc render và con số N3. **Nếu không đạt thì đổi hướng trước khi viết UI** |
| **Phase 1 (MVP)** | M1 toàn bộ · M2 toàn bộ P1 · M3: ảnh / carousel / video + fit mode, 6 effect P1, 9 visualizer, Now Playing / tiêu đề / logo · M4 P1 · M5 P1 | Làm được video mix 3 tiếng hoàn chỉnh từ đầu đến cuối |
| **Phase 2** | VHS, Fog, Rain, Custom Overlay, phản ứng theo bass, progress bar, safe area, gain từng bài, template project, thông báo | Đa dạng style |
| **Phase 3** | Parallax 2.5D, 4K, shuffle / sắp xếp thông minh | Tùy nhu cầu thật |

---

## 8. Acceptance Criteria cho MVP

- [ ] Dán 1 playlist YouTube 20 bài + kéo 10 file local (mkv, flac, m4a) → tick 25 bài → xuất 25 MP3 320kbps, không lỗi.
- [ ] Cắt 1 file mix 2 tiếng theo tracklist 30 dòng → 30 MP3 đúng mốc (sai số ≤ 0.1s).
- [ ] Mix 40 bài (~2h45m), mỗi điểm nối một preset khác nhau, chỉnh tay 3 điểm, lưu 1 preset mới → nghe thử từng điểm nối ngay trong UI.
- [ ] Các bài nghe đều âm lượng (±1 LU so với -14 LUFS), không clip ở vùng crossfade.
- [ ] Render MP4 16:9 nền ảnh dọc 9:16 (blur fill) + Preset B + Circular Radial Bars + Now Playing → video chạy hết 2h45m, tên bài đổi đúng thời điểm, nền loop không giật.
- [ ] Tắt app giữa chừng lúc render 60% → mở lại → resume, không render lại từ đầu.
- [ ] `chapters.txt` dán vào YouTube nhận đúng chapters.
