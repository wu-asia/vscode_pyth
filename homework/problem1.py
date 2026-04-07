def combine(n, i):
    if i > n:
        return 0
    elif i == 1:
        return n
    elif n == i:
        return 1
    else:
        return combine(n - 1, i - 1) + combine(n - 1, i)
    

n = int(input('请输入n:'))
i = int(input('请输入i:'))
ret = combine(n, i)
print(f'c({n}, {i})的结果是{ret}')