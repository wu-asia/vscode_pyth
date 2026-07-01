import tkinter as tk

root = tk.Tk()
root.title("测试")
root.geometry("400x300")

btn = tk.Button(root, text="Hello")
btn.pack()

root.mainloop()