# *arg 是将参数打包成元组
# **kwarg是将参数打包成字典，而且必须是偶数个参数

def func(*arg):
    avg = sum(arg) / len(arg)
    l = []
    for i in arg:
        if i > avg:
            l.append(i)
    ret = (avg, ) + tuple(l)
    return ret


t = func(10, 20, 30)
print(t)
