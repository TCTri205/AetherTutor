import pypdf
from pypdf.errors import PdfReadError
from ..core.exceptions import PermanentProcessingError
import logging

logger = logging.getLogger(__name__)

class PDFExtractor:
    """ Dịch vụ trích xuất nội dung văn bản từ file PDF. """

    def extract_text(self, file_path: str) -> str:
        """
        Trích xuất văn bản từ file PDF tại file_path.
        
        Raises:
            PermanentProcessingError: Nếu file bị mã hóa, bị hỏng hoặc không phải PDF hợp lệ.
        """
        try:
            reader = pypdf.PdfReader(file_path)
            
            # Kiểm tra mã hóa
            if reader.is_encrypted:
                logger.error(f"File PDF bị mã hóa: {file_path}")
                raise PermanentProcessingError("File PDF bị đặt mật khẩu bảo vệ. Không thể xử lý.")

            text_parts = []
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Không thể trích xuất văn bản từ trang {page_num} của {file_path}: {e}")
                    continue
            
            full_text = "\n\n".join(text_parts).strip()
            
            if not full_text:
                # Có thể là PDF dạng ảnh hoàn toàn hoặc không có text layer
                # Trong tương lai có thể tích hợp OCR ở đây. Hiện tại coi như lỗi.
                logger.warning(f"File PDF không chứa văn bản có thể trích xuất: {file_path}")
                # Chúng ta không raise lỗi ở đây để LightRAG có thể vẫn thử xử lý nếu cần, 
                # hoặc trả về chuỗi rỗng để pipeline ghi nhận.
                # Tuy nhiên theo yêu cầu phase 3, nếu "không extract được" thì nên cảnh báo.
            
            return full_text

        except PdfReadError as e:
            logger.error(f"Lỗi đọc file PDF {file_path}: {e}")
            raise PermanentProcessingError(f"File PDF không hợp lệ hoặc bị hỏng: {str(e)}")
        except Exception as e:
            if isinstance(e, PermanentProcessingError):
                raise e
            logger.error(f"Lỗi không xác định khi xử lý PDF {file_path}: {e}")
            raise PermanentProcessingError(f"Lỗi hệ thống khi đọc PDF: {str(e)}")

pdf_extractor = PDFExtractor()
