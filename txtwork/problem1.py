try:
    f = open("hello_world.txt", "r", encoding="UFT-8")
    content = f.read(10)
except Exception as e:
    f = open("hello_world.txt", "w", encoding="UFT-8")
    print('文件创建成功')

    
