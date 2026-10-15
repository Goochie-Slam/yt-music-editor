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
}

WHAT: dict[str, str] = {
    "job": "tác vụ",
    "project": "project",
    "preset": "preset",
}


def message(code: str, **kw: str) -> str:
    if "what" in kw:
        kw["what"] = WHAT.get(kw["what"], kw["what"])
    return MESSAGES.get(code, MESSAGES["internal"]).format(**kw)
