def fun(n, k):
    lst = list(range(1, n + 1))
    cnt = 0
    while len(lst) > 1:
        cnt = (cnt + k - 1) % len(lst)
        lst.pop(cnt)
    return lst[0]


n, k = map(int, input('请输入n, k:').split())
print(fun(n, k))        


