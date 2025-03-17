#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导出微信聊天记录工具

使用方法:
python export_records.py --start "2023-01-01" --end "2023-01-31" --output "my_records.json"

所有参数都是可选的:
--start: 开始时间，格式为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
--end: 结束时间，格式为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
--output: 输出文件路径，如果不指定则自动生成
"""

import argparse
import sys
import traceback
from datetime import datetime

# 尝试导入所需模块并捕获错误
try:
    from app.DataBase import init_db
    from app.export import export_chat_records_to_json
    from app.log import logger
except Exception as e:
    print(f"导入模块时出错: {str(e)}")
    print(traceback.format_exc())
    sys.exit(1)


def parse_date(date_str):
    """解析日期字符串"""
    try:
        # 尝试解析 YYYY-MM-DD HH:MM:SS 格式
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            # 尝试解析 YYYY-MM-DD 格式
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"无效的日期格式: {date_str}，请使用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS 格式")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="导出微信聊天记录到JSON文件")
    parser.add_argument("--start", help="开始时间 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--end", help="结束时间 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--debug", action="store_true", help="显示详细错误信息")
    
    args = parser.parse_args()
    
    # 解析时间范围
    time_range = None
    if args.start or args.end:
        start_time = parse_date(args.start) if args.start else datetime(1970, 1, 1)
        end_time = parse_date(args.end) if args.end else datetime.now()
        time_range = (start_time, end_time)
    
    try:
        # 初始化数据库连接
        print("正在初始化数据库连接...")
        init_db()
        
        # 导出聊天记录
        print("正在导出聊天记录...")
        output_path = export_chat_records_to_json(time_range, args.output)
        
        if output_path:
            print(f"聊天记录已成功导出到: {output_path}")
        else:
            print("导出失败，请检查日志获取详细信息。")
    except Exception as e:
        print(f"导出过程中出错: {str(e)}")
        if args.debug:
            print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)
