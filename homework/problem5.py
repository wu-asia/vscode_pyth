def is_prime(n):
    if n < 2:
        return False
    elif n == 2:
        return True
    else:
        for i in range(2, int((n**0.5)) + 1):
            if n % i == 0:
                return False
        return True
    
def fun(num, lst):
    if num <= 0 or num % 2 != 0:
        return None
    else:
        for i in range(1, num // 2 + 1):
            j = num - i
            if is_prime(i) and is_prime(j):
                lst.append((i, j))
        return lst

n = int(input('请输入一个正偶数：'))
lst = []
fun(n, lst)

if lst:
    print(f'正偶数的素数组合有：{lst}')
else:
    print('不存在')
