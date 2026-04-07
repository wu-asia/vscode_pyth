def Count(s):
    a = 0
    b = 0
    for i in s:
        if 'A' <= i <= 'Z':
            a += 1
        elif 'a' <= i <= 'z':
            b += 1
    return (a, b)

s = "aAbc"
print(Count(s))

