# Decision Log

Ghi lại mọi quyết định có ảnh hưởng lâu dài: **đã chốt gì, vì sao, ai chốt**. Thêm mục mới ở **cuối** bảng, không sửa mục cũ — nếu đổi ý thì thêm mục mới ghi "thay thế D-xx".

| ID | Ngày | Quyết định | Lý do | Chốt bởi |
|---|---|---|---|---|
| D-01 | 2026-10-12 | Web app chạy local (Python backend + UI trên trình duyệt), chỉ Windows | Render nặng phải chạy trên máy user; một người dùng, không cần cloud | PO |
| D-02 | 2026-10-12 | Transition = `fadeOut` / `fadeIn` / `overlap` (+ curve); `overlap < 0` là khoảng lặng | Một mô hình phủ được cả crossfade lẫn fade → lặng → fade | PO + Claude |
| D-03 | 2026-10-12 | Curve mặc định: equal-power | Linear hụt ~3 dB ở giữa vùng crossfade | Claude (PO ủy quyền) |
| D-04 | 2026-10-12 | 5 preset transition: Smooth Blend, Quick Mix, Long Dissolve, Radio Segue, Fade & Breathe | PO yêu cầu ~5 preset tham khảo | PO + Claude |
| D-05 | 2026-10-12 | Normalize từng bài về −14 LUFS, true-peak ≤ −1 dBTP | Mức chuẩn YouTube; crossfade giữa 2 bài lệch âm lượng sẽ bị giật | PO |
| D-06 | 2026-10-12 | Không beat-match / DJ | Ngoài nhu cầu, tăng độ phức tạp nhiều lần | PO |
| D-07 | 2026-10-12 | Nguồn audio: file local + link (YouTube, SoundCloud, Mixcloud…) qua yt-dlp.exe | PO dùng cả hai; bản `.exe` tự cập nhật được | PO |
| D-08 | 2026-10-12 | MP3 320kbps CBR, không ghi tag | PO yêu cầu | PO |
| D-09 | 2026-10-12 | Mix dạng **danh sách dọc + chip transition**, không dùng timeline ngang | Mix 3 tiếng / 40 bài trên timeline ngang không thao tác được | Claude |
| D-10 | 2026-10-12 | Cắt tracklist → mix lại; nội bộ luôn dùng WAV lossless, MP3 chỉ ở bước xuất | Tránh nén lossy chồng lớp | PO + Claude |
| D-11 | 2026-10-12 | Output 1080p mặc định; 1440p, 4K tùy chọn; 16:9 chính, có 9:16 | PO yêu cầu; 1440p giúp YouTube dùng codec tốt hơn | PO |
| D-12 | 2026-10-12 | Nguồn lệch tỉ lệ → Blur fill / Solid color / Crop fill | PO yêu cầu | PO |
| D-13 | 2026-10-12 | Tab Video dùng **timeline layer**: mọi element là 1 track, chọn & chỉnh được | Feedback UI lần 1 của PO | PO |
| D-14 | 2026-10-12 | Artwork và Nền là 2 element riêng | Cho phép thu nhỏ / dời artwork, nền tự lấp phần trống | Claude |
| D-15 | 2026-10-12 | Overlay cơ bản (video / PNG / màu-gradient-vignette) là P1 | Feedback lần 2 của PO: overlay bắt buộc | PO |
| D-16 | 2026-10-12 | Keyframe animation hoãn sang P3 | PO: chưa cần ở giai đoạn này | PO |
| D-17 | 2026-10-12 | Parallax 2.5D hoãn sang P3 | Cần AI tách lớp, hay lỗi méo mặt | Claude |
| D-18 | 2026-10-12 | Máy mục tiêu: RTX 3050 6GB, encode NVENC, fallback x264 | Máy của PO | PO |
| D-19 | 2026-10-12 | Effect / overlay / visualizer là hàm thuần của thời gian `f(t)` | Bắt buộc để chunk, resume và preview cho ra cùng một frame | Claude |
| D-20 | 2026-10-12 | Shader GLSL dùng chung cho preview (WebGL2) và render (moderngl) | Preview = Render (N6) | Claude |
| D-21 | 2026-10-15 | Render theo cách **A — vẽ mọi thứ ở từng frame**. Bỏ cách B (pre-render loop nền). Đọc frame từ GPU dạng **NV12**, encode **NVENC**, decode overlay bằng **NVDEC** | Benchmark trên PC của PO (`bench/archive/results-DUYNHA-20261015-163844.md`): A nhanh hơn B ở mọi độ phân giải (1080p 142 vs 112 fps · 1440p 91 vs 62 · 4K 29 vs 20, có 1 overlay video). B vừa chậm hơn vừa phức tạp hơn (file tạm, đồng bộ loop). NV12 nhanh hơn RGBA 12% (142 vs 127 fps). x264 dùng được làm fallback (132 fps) nhưng ăn 94% CPU. GPU chỉ chạy 17–27% → nút cổ chai là phía CPU (decode overlay, đọc frame, pipe sang FFmpeg), **tối ưu sau này nhắm vào đó, không phải shader** | PO chạy · Claude chốt |
| D-22 | 2026-10-12 | Curve `log` = `x^2.5` (fade-in), fade-out = fade-in đảo ngược thời gian cho **mọi** curve | Bản cũ trong CODING-GUIDE và mockup dùng 2 công thức không đối xứng cho in/out — QA phát hiện khi viết `curves.py` | Claude |
