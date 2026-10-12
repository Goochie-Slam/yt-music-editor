# Benchmark render — M0 / Spike S1

Script này trả lời câu hỏi quan trọng nhất trước khi code phần video: **máy RTX 3050 6GB render một mix 3 tiếng mất bao lâu?**

Nó render một cảnh giống app thật: artwork 9:16 trên nền blur, slow zoom, film grain, bụi, overlay video blend Screen, visualizer tròn và 2 dòng chữ. Toàn bộ dữ liệu được **tự sinh ra**, không cần file nào của anh.

## Chạy trên Windows (máy RTX 3050)

1. Cài **Python 3.12** từ [python.org](https://www.python.org/downloads/). Khi cài, tick **"Add python.exe to PATH"**.
2. Cập nhật driver NVIDIA lên bản mới.
3. **Nếu là laptop:** Settings → System → Display → Graphics → *Add desktop app* → chọn `bench\.venv\Scripts\python.exe` (có sau lần chạy đầu) → Options → **High performance**. Không làm bước này thì script có thể chạy trên GPU Intel, và kết quả sẽ sai.
4. **Double-click `run_bench.bat`.** Lần đầu, script tự tải FFmpeg (~100 MB) và thư viện Python.
5. Đóng các app nặng (game, Chrome nhiều tab…). Đợi khoảng **15–25 phút**.
6. Gửi **toàn bộ thư mục `bench\results`** cho Claude: file `.md`, `.json` và các ảnh `preview-*.png`.

Muốn chạy nhanh để thử: mở Command Prompt trong thư mục `bench` rồi chạy `run_bench.bat --quick` (~5 phút, kém chính xác hơn).

## Script đo gì

| Cấu hình | Ý nghĩa |
|---|---|
| `A-noov` | Vẽ mọi thứ ở từng frame, không có overlay video |
| `A-ov` | Như trên, thêm 1 overlay video full khung |
| `B-ov` | Render **1 vòng loop nền 60s** trước, sau đó decode vòng loop đó + ghép overlay, visualizer, chữ |
| `x264` | Encode bằng CPU, để so với NVENC |
| `rgba` | Đọc frame từ GPU ở dạng RGBA thay vì NV12, để đo lợi ích của việc đổi màu ngay trên GPU |

Mỗi cấu hình chạy ở **1080p / 1440p / 2160p**, mặc định 60 giây nội dung. Cột **"Dự kiến 3h"** là thời gian ước tính để render một mix 3 tiếng.

## Tùy chọn

```
run_bench.bat --quick                 # 15s mỗi cấu hình
run_bench.bat --res 1080,1440         # bỏ 4K
run_bench.bat --duration 120          # đo lâu hơn, chính xác hơn
run_bench.bat --keep                  # giữ file mp4 trong bench\work để xem
```

## Dev (Linux, không có GPU)

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
xvfb-run -a .venv/bin/python run_bench.py --res 1080 --duration 2 --encoders x264
```

Trên máy không có GPU, OpenGL chạy bằng phần mềm (llvmpipe), nên con số **không có giá trị**. Chạy kiểu này chỉ để kiểm tra script không lỗi và hình xuất ra đúng.
