"""Every user-facing backend message, in Vietnamese. Codes are stable; wording may change."""

MESSAGES: dict[str, str] = {
    "internal": "Có lỗi không mong muốn. Chi tiết đã được ghi vào file log.",
    "not_found": "Không tìm thấy {what}.",
    "invalid_input": "Dữ liệu gửi lên không hợp lệ.",
    "forbidden_host": "Yêu cầu bị chặn: chỉ chấp nhận truy cập từ chính máy này.",
    "project_exists": "Đã có project ở thư mục này.",
    "project_not_found": "Không tìm thấy project tại: {path}",
    "project_corrupt": (
        "File project bị hỏng hoặc không đọc được. Bản sao lưu nằm cạnh file (.bak1 … .bak5)."
    ),
    "project_too_new": "Project này được tạo bằng phiên bản app mới hơn. Hãy cập nhật app.",
    "project_id_mismatch": "Dữ liệu lưu không khớp với project đang mở.",
    "folder_not_found": "Thư mục không tồn tại: {path}",
    "ffmpeg_missing": "Không tìm thấy FFmpeg. Bản cài đặt có thể bị thiếu file.",
    "ffmpeg_failed": "FFmpeg báo lỗi khi xử lý.",
    "preset_builtin": "Không thể sửa hoặc xóa preset có sẵn.",
    "preset_name_taken": 'Đã có preset tên "{name}".',
    # library: files
    "file_not_found": "Không tìm thấy file: {path}",
    "unsupported_file": "Không đọc được file này — định dạng không hỗ trợ hoặc file bị hỏng.",
    "no_audio": "File không có âm thanh.",
    "decode_failed": "Giải mã âm thanh thất bại.",
    "disk_full": "Ổ đĩa không đủ chỗ: cần khoảng {need}, chỉ còn {free}.",
    "outside_project": "Đường dẫn nằm ngoài thư mục project.",
    "export_folder_invalid": "Không tạo được thư mục xuất: {path}",
    "pattern_invalid": "Mẫu tên file phải có {{title}} hoặc {{index}}.",
    "nothing_selected": "Chưa chọn bài nào.",
    # library: links (yt-dlp)
    "ytdlp_missing": "Không tìm thấy yt-dlp. Chạy lại Start.bat để app tự tải về.",
    "yt_private": "Video riêng tư.",
    "yt_unavailable": "Nội dung không còn tồn tại hoặc đã bị gỡ.",
    "yt_age": "Nội dung giới hạn độ tuổi — cần đăng nhập, app không hỗ trợ.",
    "yt_geo": "Nội dung bị chặn ở quốc gia của anh.",
    "yt_members": "Nội dung chỉ dành cho thành viên hoặc phải trả phí.",
    "yt_drm": "Nội dung có DRM — không tải được.",
    "yt_live": "Đang phát trực tiếp — chờ buổi phát kết thúc rồi thử lại.",
    "yt_bot": "Trang yêu cầu xác minh chống bot. Thử lại sau ít phút hoặc cập nhật yt-dlp.",
    "yt_rate_limited": "Bị trang chặn tạm thời vì tải quá nhiều (HTTP 429). Thử lại sau.",
    "yt_js_runtime": (
        "yt-dlp cần Node.js hoặc Deno để tải từ YouTube. Cài Node.js 22 rồi mở lại app."
    ),
    "yt_unsupported": "Link này không được hỗ trợ.",
    "yt_not_found": "Không tìm thấy nội dung (lỗi 404). Kiểm tra lại link.",
    "yt_network": "Không kết nối được tới trang. Kiểm tra mạng.",
    "yt_failed": "yt-dlp báo lỗi: {reason}",
    "ytdlp_update_failed": "Cập nhật yt-dlp thất bại.",
}

WHAT: dict[str, str] = {
    "job": "tác vụ",
    "project": "project",
    "preset": "preset",
    "item": "bài trong thư viện",
}


def message(code: str, **kw: str) -> str:
    if "what" in kw:
        kw["what"] = WHAT.get(kw["what"], kw["what"])
    return MESSAGES.get(code, MESSAGES["internal"]).format(**kw)
