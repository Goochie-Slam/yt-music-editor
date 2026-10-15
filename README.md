# YT Music Editor

App local (Windows) để sản xuất video playlist nhạc dài 1–3 tiếng: lấy audio từ file/link → xuất MP3 → ghép mix với transition → render MP4 có overlay, effect, sóng nhạc, tên bài.

> Trạng thái: **M0 (benchmark render) và M1 (khung app) xong**. Kết quả benchmark: `bench/archive/`, quyết định D-21 trong `docs/DECISIONS.md`.

## Chạy thử

- **Windows:** double-click `packaging\windows\Start.bat` (cần [uv](https://docs.astral.sh/uv/) + Node 22).
- **Dev:** `cd backend && uv sync && uv run uvicorn app.main:create_app --factory --port 8765 --reload` và `cd frontend && npm ci && npm run dev` → http://127.0.0.1:5173
- **Kiểm tra trước khi mở PR:** xem `docs/CODING-GUIDE.md` §4.

## Bắt đầu từ đâu

**Developer mới:** đọc theo thứ tự 1 → 2 → 3.

| # | File | Nội dung |
|---|---|---|
| 1 | [`docs/PROJECT-OVERVIEW.md`](docs/PROJECT-OVERVIEW.md) | Dự án là gì, vai trò, kiến trúc tóm tắt, phạm vi, roadmap, rủi ro |
| 2 | [`docs/CODING-GUIDE.md`](docs/CODING-GUIDE.md) | Stack, cấu trúc repo, data model, quy tắc kỹ thuật, test, milestone, quy trình PR/QA |
| 3 | [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) | Requirement chi tiết có ID — nguồn sự thật về chức năng |
| 4 | [`docs/UI-UX.md`](docs/UI-UX.md) | Spec từng màn hình |
| 5 | [`docs/ui-mockup.html`](docs/ui-mockup.html) | Mockup tương tác — mở bằng trình duyệt |
| 6 | [`docs/DECISIONS.md`](docs/DECISIONS.md) | Nhật ký quyết định |
| 7 | [`docs/visual-effects-reference.md`](docs/visual-effects-reference.md) | Thư viện effect & preset style |

## Vai trò
- **Product Owner:** chủ dự án — phạm vi, ưu tiên, merge PR
- **Orchestrator & QA:** Claude — tài liệu, chia task, review mọi PR
- **Developer:** code + test theo `CODING-GUIDE.md`, mở PR theo template
