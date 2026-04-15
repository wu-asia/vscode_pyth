from docx import Document

def check_repeat_words(file_path):
    doc = Document(file_path)

    found = False

    # 遍历每一段
    for para_idx, para in enumerate(doc.paragraphs, start=1):
        text = para.text.strip()
        if len(text) < 2:
            continue

        # 检查连续两个字相同
        for i in range(len(text) - 1):
            current = text[i]
            next_c = text[i + 1]

            # 只检查汉字，不检查标点、数字、字母
            if "\u4e00" <= current <= "\u9fff" and current == next_c:
                print(f"第 {para_idx} 段 发现重复：{current}{next_c}")
                print(f"内容：{text}")
                found = True

    if not found:
        print("没有发现连续重复字！")
check_repeat_words("D:\\develop\\Sources\\Python\\vscode_pyth\\test5.docx")

# import sys
# print(sys.executable)