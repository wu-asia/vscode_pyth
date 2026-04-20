import os
from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams

def pdf2txt(pdf_path, txt_path):
    with open(pdf_path, 'rb') as f:
        parser = PDFParser(f)
        doc = PDFDocument()
        parser.set_document(doc)
        doc.set_parser(parser)
        doc.initialize()
        
        rsrcmgr = PDFResourceManager()
        device = PDFPageAggregator(rsrcmgr, laparams=LAParams())
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        
        text = ''
        for page in doc.get_pages():
            interpreter.process_page(page)
            for obj in device.get_result():
                if hasattr(obj, 'get_text'):
                    text += obj.get_text()
    
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)

# 批量转换当前文件夹下所有PDF
for file in os.listdir('.'):
    if file.lower().endswith('.pdf'):
        pdf2txt(file, file[:-4] + '.txt')