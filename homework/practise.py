def fun(*arg):
    l = [i for i in arg if i > 10]
    return l

print(fun(10, 20, 40))

l = [1, 2, 3, 5, 6]
print(l[:3])
print(l[3:])
print(l[-1])
print(l[:-2])
print(l[-2:])
#[:]是左闭右开的形式

print('=================')
l1 = [1, 2, 3, 4]
l2 = list(map(lambda x : x**2, l1))
print(l1)
print(l2)
print('+++++++++++++++')

#num = list(map(int, input().split(' ')))
#print(num)

a = [1, 2, 3]
b = [10, 20, 30]
c = list(map(lambda x, y : x + y, a, b))
print(a, b, c, sep='\n')

d = dict(zip(a, b))
print(d)
print(type(d))

d1 = dict(zip(range(0, len(b)), b))
print(d1)
