import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"D:\Program Files\Tesseract-OCR\tesseract.exe"
print(pytesseract.get_tesseract_version())