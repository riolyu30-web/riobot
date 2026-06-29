from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def _get_ocr():
    # 使用 rapidocr_onnxruntime 库，轻量且不需要复杂的 PyTorch/PaddlePaddle 环境
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as e:
        raise ImportError("请先安装依赖: uv pip install rapidocr_onnxruntime") from e
    
    return RapidOCR()

def get_text(image_path: str) -> str:
    """
    使用 RapidOCR 提取图片中的全部文本
    """
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"image not found: {image_file}")

    ocr = _get_ocr()
    
    # RapidOCR 的调用返回 (result, elapse)
    # result 的格式通常为: [ (box坐标, 识别文本, 置信度), ... ]
    result, _ = ocr(str(image_file))
    
    if not result:
        return ""
        
    texts = []
    for item in result:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            text = item[1]
            if text:
                texts.append(str(text))
                
    return texts

if __name__ == "__main__":
    # 测试代码
    import sys
    test_image = "C:\\Users\\xunyue\\Desktop\\103.jpg"
    try:
        print(get_text(test_image))
    except Exception as e:
        print(f"Error: {e}")
