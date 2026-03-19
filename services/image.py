"""
图片处理服务模块
封装图片验证、压缩等处理逻辑
"""
import io
import logging
from typing import Tuple, Optional
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# 允许的扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# HEIF/HEIC 支持
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
    ALLOWED_EXTENSIONS.update({'heic', 'heif'})
except ImportError:
    HEIC_SUPPORTED = False
    logger.debug("pillow_heif not found, HEIC support disabled")


class ImageValidator:
    """
    图片验证器
    验证上传文件是否为合法的图片
    """

    @staticmethod
    def is_allowed(filename: str) -> bool:
        """
        检查文件扩展名是否允许

        Args:
            filename: 文件名

        Returns:
            是否允许上传
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def validate_mime(file_stream) -> Tuple[bool, str]:
        """
        验证上传文件的 MIME 类型是否为图片

        通过读取文件头魔法字节验证，防止恶意文件上传

        Args:
            file_stream: 文件流

        Returns:
            (是否有效，MIME 类型或错误信息)
        """
        try:
            # 读取文件头（魔法字节）
            header = file_stream.read(16)
            file_stream.seek(0)  # 重置指针
            if len(header) < 3:
                return False, "文件太小，无法验证"

            # 检测常见图片格式
            # JPEG: FF D8 FF
            if header[:3] == b'\xFF\xD8\xFF':
                return True, 'image/jpeg'

            # PNG: 89 50 4E 47 0D 0A 1A 0A
            if header[:8] == b'\x89PNG\r\n\x1a\n':
                return True, 'image/png'

            # GIF: 47 49 46 38
            if header[:6] in (b'GIF87a', b'GIF89a'):
                return True, 'image/gif'

            # WebP: RIFF....WEBP
            if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                return True, 'image/webp'

            # HEIC: ftypheic 或 ftypheix 等
            if header[:4] == b'\x00\x00\x00\x1c' and b'ftyp' in header[4:8]:
                return True, 'image/heic'

            # 尝试用 Pillow 打开验证（兜底方案）
            # 注意：不调用 img.verify()，verify() 后对象不可再使用且格式读取未定义
            file_stream.seek(0)
            try:
                with Image.open(file_stream) as img:
                    fmt = img.format.lower() if img.format else 'unknown'
                file_stream.seek(0)
                return True, f'image/{fmt}'
            except Exception:
                pass

            return False, "无法识别的文件格式，可能不是有效的图片"

        except Exception as e:
            return False, f"文件验证失败：{str(e)}"


class ImageProcessor:
    """
    图片处理器
    提供智能压缩、格式转换等功能
    """

    @staticmethod
    def smart_compress(source_file, target_size_mb: float = 3.0,
                       max_resolution_px: int = 3840) -> io.BytesIO:
        """
        智能图片压缩处理

        目标：
        - 文件大小：target_size_mb 以内（默认 3MB）
        - 画质：最大化保留（quality 75-95）
        - 方向：自动修正 EXIF 方向
        - 分辨率：max_resolution_px 封顶（默认 4K）

        Args:
            source_file: 源文件流
            target_size_mb: 目标文件大小（MB）
            max_resolution_px: 最大分辨率（像素）

        Returns:
            压缩后的 BytesIO 对象
        """
        try:
            target_size = int(target_size_mb * 1024 * 1024)

            # 1. 预处理 (Open & Orient)
            # 使用 with 确保文件句柄释放；转换/resize 产生新对象后原始 img 即可关闭
            with Image.open(source_file) as raw_img:
                # 固定方向
                img = ImageOps.exif_transpose(raw_img)

                # 格式统一 (JPG 不支持透明)
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')

                # 保留 EXIF
                exif_data = img.info.get('exif')

                # 2. Resizing Helper (LANCZOS)
                def resize_to_limit(image, limit_px):
                    w, h = image.size
                    if max(w, h) > limit_px:
                        scale = limit_px / max(w, h)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        return image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    return image

                # 初始尺寸限制（在 with 块内完成，保证 raw_img 可用）
                current_img = resize_to_limit(img, max_resolution_px)
                # 保存一份 original-source 尺寸用于第二轮降级（resize_to_limit 返回新对象）
                original_for_round2 = resize_to_limit(img, max_resolution_px)

            output_buffer = io.BytesIO()

            # 3. 循环压缩 - 第一轮 (quality 95 -> 75)
            quality = 95
            while quality >= 75:
                output_buffer.seek(0)
                output_buffer.truncate()

                save_config = {
                    "format": "JPEG",
                    "quality": quality,
                    "optimize": True,
                    "subsampling": 0
                }
                if exif_data:
                    save_config["exif"] = exif_data

                current_img.save(output_buffer, **save_config)

                # Check size
                if output_buffer.tell() <= target_size:
                    output_buffer.seek(0)
                    return output_buffer

                quality -= 5

            # 4. 第二轮：第一轮失败 (即 quality=75 仍 > target_size)
            # 分辨率降级 -> 2560px
            logger.warning(f"Compress: High quality failed, resizing to 2560px...")
            current_img = resize_to_limit(original_for_round2, 2560)

            quality = 90
            while quality >= 70:
                output_buffer.seek(0)
                output_buffer.truncate()

                save_config = {
                    "format": "JPEG",
                    "quality": quality,
                    "optimize": True,
                    "subsampling": 0
                }
                if exif_data:
                    save_config["exif"] = exif_data

                current_img.save(output_buffer, **save_config)

                if output_buffer.tell() <= target_size:
                    output_buffer.seek(0)
                    return output_buffer

                quality -= 5

            # Final Fallback (if still huge, return the last attempt)
            output_buffer.seek(0)
            logger.warning("Compress: Could not reach target size, returning best effort")
            return output_buffer

        except Exception as e:
            logger.error(f"Smart Compress Error: {e}")
            # Fallback: return original
            source_file.seek(0)
            return io.BytesIO(source_file.read())

    @staticmethod
    def convert_heic_to_jpg(source_file) -> io.BytesIO:
        """
        将 HEIC/HEIF 格式转换为 JPG

        Args:
            source_file: HEIC 文件流

        Returns:
            JPG 格式的 BytesIO 对象
        """
        if not HEIC_SUPPORTED:
            raise ValueError("HEIC support not available (pillow_heif not installed)")

        try:
            with Image.open(source_file) as img:
                img = ImageOps.exif_transpose(img)
                img = img.convert('RGB')  # HEIC 可能包含透明通道

                output = io.BytesIO()
                img.save(output, format='JPEG', quality=95, optimize=True)
                output.seek(0)
                return output

        except Exception as e:
            logger.error(f"HEIC to JPG conversion error: {e}")
            raise
