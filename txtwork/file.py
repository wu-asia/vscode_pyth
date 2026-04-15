f = open('d:/Desktop/bill.txt', 'r', encoding='UTF-8')
fw = open('d:/Desktop/bill.txt', 'w', encoding='UTF-8')
for line in f:
    line = line.strip()
    if line.split(',')[4] == '测试':
        continue
    fw.write(line)
    fw.write('\n')

print('success')
f.close()
fw.close()
