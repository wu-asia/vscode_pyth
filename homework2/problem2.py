import xlwt

wb = xlwt.Workbook()

ws = wb.add_sheet('sheet1')

data = [
    ['name', 'age', 'grade'],
    ['zhangsan', 20, 90],
    ['lisi', 30, 80],
    ['wangwu', 25, 70]
]

for row, lst_data in enumerate(data):
    for col, val in enumerate(lst_data):
        ws.write(row, col, val)

wb.save('test2.xls')

print('success')

import xlrd

r_wb = xlrd.open_workbook('test2.xls')

r_ws = r_wb.sheet_by_name('sheet1')

row = r_ws.nrows
col = r_ws.ncols

for r in range(row):
    for c in range(col):
        print(r_ws.cell_value(r, c), end=' ')
    print('\n')

