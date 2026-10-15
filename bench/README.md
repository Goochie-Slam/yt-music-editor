# Hướng dẫn chạy Benchmark render (M0 / Spike S1)

**Mục đích:** đo xem máy RTX 3050 6GB render một mix 3 tiếng mất bao lâu, để chốt cách làm phần Video (quyết định D-21). Toàn bộ phần video của app đang chờ con số này.

**Tổng thời gian:** chuẩn bị ~10–15 phút, máy tự chạy ~15–25 phút.

Script render một cảnh giống app thật: artwork dọc trên nền blur, slow zoom, film grain, bụi bay, overlay video blend Screen, visualizer tròn và 2 dòng chữ. Mọi dữ liệu đều **tự sinh ra** — không cần file nhạc hay ảnh nào của anh.

---

## 1. Công cụ & dependency cần có

| # | Thứ cần có | Cách lấy | Ghi chú |
|---|---|---|---|
| 1 | Windows 10 / 11 64-bit | — | |
| 2 | **Driver NVIDIA mới nhất** | [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx) hoặc app NVIDIA | Driver cũ có thể làm NVENC không chạy |
| 3 | **Python 3.12** | [python.org/downloads](https://www.python.org/downloads/) → bản 3.12.x, **hoặc** Microsoft Store → "Python 3.12" | python.org: **phải tick "Add python.exe to PATH"**. Microsoft Store: tự có PATH, không cần làm gì |
| 4 | Mã nguồn dự án | Tải ZIP ([link ở bước 2.1](#21-tải-mã-nguồn)) | |
| 5 | Kết nối Internet | — | Chỉ cần lần chạy đầu |
| 6 | Ổ đĩa trống **≥ 3 GB** | — | FFmpeg, thư viện Python, file video tạm |

**Script tự tải, anh không cần cài:**

| Thứ | Dung lượng | Để làm gì |
|---|---|---|
| FFmpeg (bản gyan.dev, có NVENC) | ~100 MB | Encode video |
| moderngl, numpy, Pillow, psutil | ~60 MB | Vẽ hình bằng GPU, đo CPU |

`nvidia-smi` (dùng để đo % GPU và VRAM) đã có sẵn khi cài driver NVIDIA.

---

## 2. Quy trình chạy

### 2.1 Tải mã nguồn

1. Mở link: **https://github.com/Goochie-Slam/yt-music-editor/archive/refs/heads/claude/audio-video-editor-app-8ssfmv.zip** (sau khi PR #1 được merge thì dùng link [main](https://github.com/Goochie-Slam/yt-music-editor/archive/refs/heads/main.zip)).
2. Giải nén, rồi **đổi tên thư mục thành `C:\ytme`** — đường dẫn ngắn, không dấu, không khoảng trắng cho dễ.
3. Kiểm tra: phải có file `C:\ytme\bench\run_bench.bat`.

### 2.2 Chuẩn bị máy (rất quan trọng — làm sai thì số đo sai)

- [ ] **Nếu là laptop:** cắm sạc, và bắt GPU NVIDIA chạy thay vì GPU Intel:
  NVIDIA Control Panel → *Manage 3D settings* → *Global Settings* → *Preferred graphics processor* → **High-performance NVIDIA processor** → *Apply*.
- [ ] Power plan: *Settings → System → Power* → **Best performance**.
- [ ] Tắt các app nặng: game, Chrome nhiều tab, phần mềm render/stream, OBS…
- [ ] Tắt chế độ ngủ trong lúc chạy: *Settings → System → Power → Screen and sleep* → **Never** (đặt lại sau cũng được).

### 2.3 Chạy

1. Mở `C:\ytme\bench\`, **double-click `run_bench.bat`**.
2. Lần đầu, cửa sổ đen sẽ tự tải FFmpeg và thư viện (mất vài phút, tùy mạng).
3. Kiểm tra 2 dòng đầu tiên in ra:
   ```
   GPU OpenGL : NVIDIA GeForce RTX 3050 ...      ← PHẢI có chữ NVIDIA
   FFmpeg     : ffmpeg version ...
   ```
   - Nếu dòng GPU hiện **Intel** hoặc có cảnh báo `⚠ OpenGL KHÔNG chạy trên card NVIDIA` → đóng cửa sổ, làm lại bước laptop ở 2.2, chạy lại.
   - Nếu có dòng `⚠ h264_nvenc không dùng được` → cập nhật driver NVIDIA, chạy lại.
4. Script đo **11 cấu hình**, mỗi cấu hình in 1 dòng, ví dụ:
   ```
   [3/11] 1080p-B-ov-nvenc-nv12 … 142.3 fps (4.74× realtime) → mix 3h ≈ 0.7 giờ
   ```
   **Không dùng máy** trong lúc chạy (~15–25 phút).
5. Khi thấy dòng `Xong. Gui toan bo thu muc bench\results cho Claude.` là hoàn tất. Bảng tổng kết hiện ngay phía trên.

**Muốn chạy thử nhanh trước** (~5 phút, kém chính xác): mở Command Prompt trong `C:\ytme\bench` rồi gõ `run_bench.bat --quick`. Kết quả để gửi Claude thì **chạy bản đầy đủ** (double-click).

### 2.4 Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `[!] Can cai Python 3.12` | Mở Command Prompt **mới**, gõ `python --version`. **Cài từ Microsoft Store:** vào *Settings → Apps → Advanced app settings → App execution aliases* → **bật ON** `python.exe` / `python3.exe`; nếu vẫn lỗi, thêm `%LOCALAPPDATA%\Microsoft\WindowsApps` vào PATH. **Cài từ python.org:** cài lại và tick *Add python.exe to PATH*; nếu `python` mở ra Microsoft Store thì **tắt** 2 alias trên |
| `[!] Tai FFmpeg that bai` | Tải tay `ffmpeg-release-essentials.zip` từ [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/), giải nén, đổi tên thư mục bên trong thành `ffmpeg` và đặt vào `C:\ytme\bench\` (sao cho có `C:\ytme\bench\ffmpeg\bin\ffmpeg.exe`) |
| GPU hiện Intel / llvmpipe | Làm lại bước laptop ở 2.2 |
| Một cấu hình báo `LỖI: …` | Không sao — script vẫn chạy tiếp các cấu hình khác. Cứ gửi kết quả, lỗi cũng được ghi vào file |
| Windows SmartScreen chặn file `.bat` | Bấm *More info* → *Run anyway* |
| Cửa sổ đóng ngay không kịp đọc | Mở Command Prompt, `cd C:\ytme\bench`, gõ `run_bench.bat` để cửa sổ giữ lại |

---

## 3. Nơi gửi kết quả

Kết quả nằm trong **`C:\ytme\bench\results\`**:

| File | Nội dung | Gửi? |
|---|---|---|
| `results-<tên máy>-<ngày giờ>.md` | Bảng tổng kết dễ đọc | ✅ **Bắt buộc** |
| `results-<tên máy>-<ngày giờ>.json` | Số liệu chi tiết + thông tin máy | ✅ **Bắt buộc** |
| `preview-*.png` | Ảnh 1 frame của từng cấu hình | ✅ Gửi 2–3 ảnh là đủ (ví dụ `preview-1080p-A-ov-nvenc-nv12.png`) |

**Cách gửi — chọn 1 trong 3 (ưu tiên từ trên xuống):**

1. **Gửi thẳng vào cuộc chat với Claude:** kéo thả file `.md`, `.json` và 2–3 ảnh preview vào ô chat, kèm tin nhắn **`done`**.
2. **Nếu chat không nhận file:** mở file `.md` bằng Notepad → *Ctrl+A* → *Ctrl+C* → dán vào chat, kèm **`done`**. Làm tương tự với file `.json`.
3. **Qua GitHub:** nén cả thư mục `results` thành ZIP, vào [Issues → New issue](https://github.com/Goochie-Slam/yt-music-editor/issues/new) với tiêu đề `M0 benchmark results`, kéo thả file ZIP vào và dán nội dung file `.md` vào phần mô tả. Sau đó nhắn **`done`** trong chat.

**Sau khi nhận được kết quả, Claude sẽ:**

- Kiểm tra số liệu có hợp lệ không (GPU đúng là NVIDIA, NVENC chạy, không có cấu hình lỗi bất thường).
- Chốt cách render A hay B, ghi vào `docs/DECISIONS.md` (D-21).
- Cập nhật mục tiêu tốc độ N3 trong `docs/REQUIREMENTS.md` bằng số thật, và báo anh nên dùng mặc định 1080p hay 1440p.

---

## Phụ lục — script đo gì

| Cấu hình | Ý nghĩa |
|---|---|
| `A-noov` | Vẽ mọi thứ ở từng frame, không có overlay video |
| `A-ov` | Như trên, thêm 1 overlay video full khung |
| `B-ov` | Render **1 vòng loop nền 60s** trước, sau đó decode vòng loop đó + ghép overlay, visualizer, chữ |
| `x264` | Encode bằng CPU, để so với NVENC |
| `rgba` | Đọc frame từ GPU ở dạng RGBA thay vì NV12 — đo lợi ích của việc đổi màu ngay trên GPU |

Mỗi cấu hình chạy ở **1080p / 1440p / 2160p**, mặc định 60 giây nội dung. Cột **"Dự kiến 3h"** là thời gian ước tính để render một mix 3 tiếng.

Tùy chọn dòng lệnh:

```
run_bench.bat --quick                 # 15s mỗi cấu hình
run_bench.bat --res 1080,1440         # bỏ 4K
run_bench.bat --duration 120          # đo lâu hơn, chính xác hơn
run_bench.bat --keep                  # giữ file mp4 trong bench\work để xem
```

### Dành cho dev (Linux, không có GPU)

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
xvfb-run -a .venv/bin/python run_bench.py --res 1080 --duration 2 --encoders x264
```

Không có GPU thì OpenGL chạy bằng phần mềm (llvmpipe), nên con số **không có giá trị**. Chạy kiểu này chỉ để kiểm tra script không lỗi và hình xuất ra đúng.
