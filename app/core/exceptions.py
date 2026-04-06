class PermanentProcessingError(Exception):
    """
    Lỗi không thể phục hồi được trong quá trình xử lý tài liệu.
    Ví dụ: PDF bị hỏng, bị mã hóa mật khẩu, hoặc định dạng không hỗ trợ.
    Worker sẽ không retry khi gặp lỗi này.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
