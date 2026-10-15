## Tóm tắt
<!-- PR này làm gì, 1–3 câu -->

## Requirement
<!-- ID trong docs/REQUIREMENTS.md. Ghi rõ đủ hay một phần -->
- [ ] F_._ — đủ / một phần (phần còn thiếu: …)

## Cách đã test
<!-- Lệnh đã chạy + kết quả + máy/OS -->
- OS / máy:
- Lệnh:
- Kết quả:

## Ảnh chụp / GIF (bắt buộc nếu đổi UI)
<!-- Đặt cạnh màn hình tương ứng trong docs/ui-mockup.html -->

## Chỗ lệch khỏi spec
<!-- Không có thì ghi "Không". Có thì ghi lý do; quyết định lâu dài → thêm vào docs/DECISIONS.md -->

## Checklist (docs/CODING-GUIDE.md §11)
- [ ] CI xanh trên windows-latest
- [ ] ruff · mypy · ESLint · tsc không lỗi
- [ ] Test theo §8.1 (gồm ca biên)
- [ ] Chuỗi UI nằm trong i18n/vi.json
- [ ] Đã thử đường dẫn có dấu tiếng Việt + khoảng trắng
- [ ] Không `shell=True`, không nén lossy chồng lớp, effect thuần f(t)
- [ ] Không commit nhạc / video / ảnh có bản quyền
- [ ] Đổi schema → có migration + đã sinh lại type
