"""
基于 tkinter 的学生成绩录入与统计系统
Author: wu-asia
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import csv
import os

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class StudentScoreSystem:

    def __init__(self):
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("学生成绩录入与统计系统")
        self.root.geometry("800x650")
        # 禁止缩放窗口
        self.root.resizable(False, False)

        # 数据列表
        self.students = []
        # 新增：学号固定位数，初始为空未设置
        self.id_digit = None

        # 创建界面
        self.create_widgets()

        # 读取CSV数据
        self.load_data()

        # 显示数据
        self.refresh_tree()

    # 创建界面
    def create_widgets(self):
        # ========== 新增：学号位数设置区域 ==========
        digit_frame = tk.LabelFrame(self.root, text="学号位数设置", padx=10, pady=10)
        digit_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(digit_frame, text="设定学号位数：").grid(row=0, column=0, padx=5, pady=5)
        self.entry_id_digit = tk.Entry(digit_frame, width=10)
        self.entry_id_digit.grid(row=0, column=1, padx=5)
        tk.Button(digit_frame, text="确认设置", command=self.set_id_digit).grid(row=0, column=2, padx=10)
        self.label_digit_tip = tk.Label(digit_frame, text="当前未设置学号位数", fg="red")
        self.label_digit_tip.grid(row=0, column=3, padx=20)

        # ========== 学生信息录入区域 ==========
        input_frame = tk.LabelFrame(self.root, text="学生信息录入", padx=10, pady=10)
        input_frame.pack(fill="x", padx=10, pady=10)

        # 学号
        tk.Label(input_frame, text="学号：").grid(row=0, column=0, padx=5, pady=5)
        self.entry_id = tk.Entry(input_frame, width=20)
        self.entry_id.grid(row=0, column=1, padx=5)

        # 姓名
        tk.Label(input_frame, text="姓名：").grid(row=0, column=2, padx=5)
        self.entry_name = tk.Entry(input_frame, width=20)
        self.entry_name.grid(row=0, column=3, padx=5)

        # 成绩
        tk.Label(input_frame, text="成绩：").grid(row=0, column=4, padx=5)
        self.entry_score = tk.Entry(input_frame, width=20)
        self.entry_score.grid(row=0, column=5, padx=5)

        # 按钮区域
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="添加",
            width=12,
            command=self.add_student
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            button_frame,
            text="删除",
            width=12,
            command=self.delete_student
        ).grid(row=0, column=1, padx=10)

        tk.Button(
            button_frame,
            text="保存",
            width=12,
            command=self.save_data
        ).grid(row=0, column=2, padx=10)

        tk.Button(
            button_frame,
            text="统计",
            width=12,
            command=self.statistics
        ).grid(row=0, column=3, padx=10)

        # Treeview表格区域
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill="both", expand=True, padx=10)

        columns = ("id", "name", "score")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        self.tree.heading("id", text="学号")
        self.tree.heading("name", text="姓名")
        self.tree.heading("score", text="成绩")
        self.tree.column("id", width=180, anchor="center")
        self.tree.column("name", width=180, anchor="center")
        self.tree.column("score", width=120, anchor="center")

        # 滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 统计信息区域
        stat_frame = tk.LabelFrame(self.root, text="统计信息")
        stat_frame.pack(fill="x", padx=10, pady=10)

        self.label_avg = tk.Label(stat_frame, text="平均分：0")
        self.label_avg.grid(row=0, column=0, padx=20, pady=5)
        self.label_max = tk.Label(stat_frame, text="最高分：0")
        self.label_max.grid(row=0, column=1, padx=20)
        self.label_min = tk.Label(stat_frame, text="最低分：0")
        self.label_min.grid(row=0, column=2, padx=20)
        self.label_pass = tk.Label(stat_frame, text="及格人数：0")
        self.label_pass.grid(row=1, column=0, padx=20, pady=5)
        self.label_fail = tk.Label(stat_frame, text="不及格人数：0")
        self.label_fail.grid(row=1, column=1, padx=20)

    # 设置学号固定位数
    def set_id_digit(self):
        digit_str = self.entry_id_digit.get().strip()
        # 校验输入为正整数
        try:
            digit = int(digit_str)
            if digit <= 0:
                messagebox.showerror("错误", "位数必须是大于0的数字！")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入合法数字作为学号位数！")
            return
        # 保存位数并更新提示
        self.id_digit = digit
        self.label_digit_tip.config(text=f"当前学号固定位数：{digit}位", fg="green")
        messagebox.showinfo("设置成功", f"学号已限定为{digit}位纯数字")

    # 增加学生（新增姓名长度、学号位数双重校验）
    def add_student(self):
        # 先判断是否设置了学号位数
        if self.id_digit is None:
            messagebox.showwarning("提示", "请先设置学号固定位数！")
            return

        # 获取输入内容
        stu_id = self.entry_id.get().strip()
        name = self.entry_name.get().strip()
        score = self.entry_score.get().strip()

        # 输入空值校验
        if stu_id == "":
            messagebox.showerror("输入错误", "学号不能为空！")
            return
        if name == "":
            messagebox.showerror("输入错误", "姓名不能为空！")
            return
        if score == "":
            messagebox.showerror("输入错误", "成绩不能为空！")
            return

        # 1. 学号校验：必须纯数字 + 长度等于设定位数
        if not stu_id.isdigit():
            messagebox.showerror("输入错误", f"学号必须为纯数字！")
            return
        if len(stu_id) != self.id_digit:
            messagebox.showerror("输入错误", f"学号必须为{self.id_digit}位数字，当前输入{len(stu_id)}位！")
            return

        # 2. 姓名校验：字符长度≤4
        if len(name) > 4:
            messagebox.showerror("输入错误", f"姓名不能超过4个字符，当前输入{len(name)}位！")
            return

        # 成绩数字校验 + 范围
        try:
            score = float(score)
        except ValueError:
            messagebox.showerror("输入错误", "成绩必须是数字！")
            return
        if score < 0 or score > 100:
            messagebox.showerror("输入错误", "成绩必须在0~100之间！")
            return

        # 学号不能重复
        for stu in self.students:
            if stu["id"] == stu_id:
                messagebox.showerror("输入错误", "该学号已经存在！")
                return

        # 添加数据
        self.students.append({"id": stu_id, "name": name, "score": score})
        self.refresh_tree()

        # 清空输入框
        self.entry_id.delete(0, tk.END)
        self.entry_name.delete(0, tk.END)
        self.entry_score.delete(0, tk.END)
        messagebox.showinfo("成功", "学生成绩添加成功！")

    # 删除学生
    def delete_student(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择需要删除的记录！")
            return
        result = messagebox.askyesno("确认删除", "确定删除该条成绩记录吗？")
        if not result:
            return
        item = self.tree.item(selected[0])
        values = item["values"]
        stu_id = str(values[0])
        for stu in self.students:
            if stu["id"] == stu_id:
                self.students.remove(stu)
                break
        self.refresh_tree()
        messagebox.showinfo("成功", "删除成功！")

    # 刷新表格
    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for stu in self.students:
            self.tree.insert("", tk.END, values=(stu["id"], stu["name"], stu["score"]))

    # 保存CSV
    def save_data(self):
        try:
            with open("students.csv", "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["学号", "姓名", "成绩"])
                for stu in self.students:
                    writer.writerow([stu["id"], stu["name"], stu["score"]])
            messagebox.showinfo("保存成功", "成绩数据已保存到 students.csv")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    # 加载CSV
    def load_data(self):
        if not os.path.exists("students.csv"):
            return
        try:
            with open("students.csv", "r", newline="", encoding="utf-8-sig") as file:
                reader = csv.reader(file)
                next(reader, None)
                self.students.clear()
                for row in reader:
                    if len(row) != 3:
                        continue
                    self.students.append({"id": row[0], "name": row[1], "score": float(row[2])})
        except Exception as e:
            messagebox.showerror("读取失败", str(e))

    # 统计功能
    def statistics(self):
        if len(self.students) == 0:
            messagebox.showwarning("提示", "暂无学生成绩数据！")
            return
        scores = [stu["score"] for stu in self.students]
        average = sum(scores) / len(scores)
        maximum = max(scores)
        minimum = min(scores)
        pass_num = sum(1 for s in scores if s >= 60)
        fail_num = len(scores) - pass_num

        self.label_avg.config(text=f"平均分：{average:.2f}")
        self.label_max.config(text=f"最高分：{maximum:.2f}")
        self.label_min.config(text=f"最低分：{minimum:.2f}")
        self.label_pass.config(text=f"及格人数：{pass_num}")
        self.label_fail.config(text=f"不及格人数：{fail_num}")
        messagebox.showinfo("统计完成", "成绩统计已更新！")

    # 启动程序
    def run(self):
        self.root.mainloop()


# 程序入口
if __name__ == "__main__":
    app = StudentScoreSystem()
    app.run()