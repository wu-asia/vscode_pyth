"""
实验七：数据分析与可视化
Author : wu-asia
"""

import csv
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt



# Matplotlib 中文设置
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False


# 生成营业数据
def generate_sales_data(filename):
    """
    生成2025年饭店营业额数据

    参数：
        filename：CSV文件名称

    功能：
        1. 随机生成300天营业数据
        2. 营业额500~1500
        3. 10%的营业额设置为NaN
    """

    # 构造2025年的所有日期
    start_date = datetime(2025, 1, 1)

    all_dates = []

    for i in range(365):
        current = start_date + timedelta(days=i)
        all_dates.append(current)

    # 随机抽取300天营业
    business_days = random.sample(all_dates, 300)

    # 日期排序
    business_days.sort()

    data = []

    for day in business_days:

        sales = random.randint(500, 1500)

        # 10%概率设置为空值
        if random.random() < 0.1:
            sales = np.nan

        data.append([
            day.strftime("%Y-%m-%d"),
            sales
        ])

    # 写入CSV
    with open(filename,
              "w",
              newline="",
              encoding="utf-8-sig") as file:

        writer = csv.writer(file)

        writer.writerow(["Date", "Sales"])

        writer.writerows(data)

    print("CSV文件生成完成！")


# 读取数据
def load_data(filename):
    """
    使用pandas读取CSV文件
    """

    df = pd.read_csv(filename)

    print("\n读取的数据：")
    print(df.head())

    return df


# 删除缺失值
def remove_nan(df):
    """
    删除所有缺失值
    """

    print("\n删除缺失值前：")

    print(df.isnull().sum())

    df = df.dropna()

    print("\n删除缺失值后：")

    print(df.isnull().sum())

    return df


# 每日营业额折线图

def draw_daily_line(df):
    """
    绘制每日营业额折线图
    保存为 first.jpg
    """

    plt.figure(figsize=(12, 6))

    plt.plot(
        pd.to_datetime(df["Date"]),
        df["Sales"],
        color="blue",
        linewidth=1
    )

    plt.title("2025年每日营业额")

    plt.xlabel("日期")

    plt.ylabel("营业额（元）")

    plt.grid(True)

    plt.xticks(rotation=45)

    plt.tight_layout()

    plt.savefig("first.jpg", dpi=300)

    plt.close()

    print("first.jpg 保存成功！")

# 每月营业额统计
def monthly_statistics(df):
    """
    按月份统计营业额

    返回：
        month_sales：每月营业额Series
    """

    # 转换为日期类型
    df["Date"] = pd.to_datetime(df["Date"])

    # 提取月份
    df["Month"] = df["Date"].dt.month

    # 按月份求和
    month_sales = df.groupby("Month")["Sales"].sum()

    print("\n每月营业额统计：")
    print(month_sales)

    return month_sales


# 每月营业额柱状图
def draw_month_bar(month_sales):
    """
    绘制每月营业额柱状图
    保存：second.jpg
    """

    plt.figure(figsize=(10, 6))

    plt.bar(
        month_sales.index.astype(str),
        month_sales.values,
        color="orange"
    )

    plt.title("2025年每月营业额")

    plt.xlabel("月份")

    plt.ylabel("营业额（元）")

    plt.grid(axis="y")

    plt.tight_layout()

    plt.savefig("second.jpg", dpi=300)

    plt.close()

    print("second.jpg 保存成功！")


# 最大涨幅月份

def save_max_growth_month(month_sales):
    """
    找出相邻两个月最大涨幅

    保存：
        maxMonth.txt
    """

    # 相邻月份营业额差值
    growth = month_sales.diff()

    # 找到最大涨幅月份
    max_month = growth.idxmax()

    max_growth = growth.max()

    with open(
            "maxMonth.txt",
            "w",
            encoding="utf-8") as file:

        file.write("2025年营业额最大涨幅月份\n")
        file.write("-------------------------\n")
        file.write(f"月份：{max_month}月\n")
        file.write(f"涨幅：{max_growth:.2f} 元\n")

    print("maxMonth.txt 保存成功！")


# 季度统计
def quarter_statistics(df):
    """
    按季度统计营业额
    返回：quarter_sales
    """

    # 根据月份计算季度
    df["Quarter"] = ((df["Month"] - 1) // 3) + 1

    quarter_sales = df.groupby("Quarter")["Sales"].sum()

    print("\n季度营业额统计：")

    print(quarter_sales)

    return quarter_sales


# 季度营业额饼图
def draw_quarter_pie(quarter_sales):
    """
    绘制季度营业额饼图
    保存： third.jpg
    """

    plt.figure(figsize=(8, 8))

    labels = [
        "第一季度",
        "第二季度",
        "第三季度",
        "第四季度"
    ]

    plt.pie(
        quarter_sales.values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90
    )

    plt.title("2025年各季度营业额分布")

    plt.savefig("third.jpg", dpi=300)

    plt.close()

    print("third.jpg 保存成功！")


# 主函数
def main():

    filename = "2025_restaurant_sales.csv"

    # 生成CSV数据
    generate_sales_data(filename)

    # 读取数据
    df = load_data(filename)

    # 删除缺失值
    df = remove_nan(df)

    # 绘制每日营业额折线图
    draw_daily_line(df)

    # 月统计
    month_sales = monthly_statistics(df)

    # 月柱状图
    draw_month_bar(month_sales)

    # 最大涨幅月份
    save_max_growth_month(month_sales)

    # 季度统计
    quarter_sales = quarter_statistics(df)

    # 季度饼图
    draw_quarter_pie(quarter_sales)

    print("\n")
    print("实验完成！")
    print("\n")


# 程序入口
if __name__ == "__main__":

    main()