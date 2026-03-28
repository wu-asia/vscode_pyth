# # a = int(input('input a number'))
# # print(a)

# a = 10
# print(a)
# print("input a")
# a = int(input())
# print("input b")
# b = int(input())
# print(a + b)

# s = int(input("input a number"))

# for i in range(0, s):
#     print(i)

def compute(fun, a, b):
    return fun(a, b)


def add(a, b):
    return a + b

print(compute(add, 10, 20))

