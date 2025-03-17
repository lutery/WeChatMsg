#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版微信聊天记录导出工具

这个脚本提供了一个简化版的导出功能，不依赖于完整的WeChatMsg代码库。
它直接连接到微信数据库并导出指定时间范围内的聊天记录到JSON文件。

使用方法:
python simple_export.py --db-path "path/to/MSG.db" --contact-db-path "path/to/MicroMsg.db" --start "2023-01-01" --end "2023-01-31" --output "my_records.json"

参数说明:
--db-path: 消息数据库路径 (MSG.db)
--contact-db-path: 联系人数据库路径 (MicroMsg.db)
--start: 开始时间，格式为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
--end: 结束时间，格式为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
--output: 输出文件路径，如果不指定则自动生成

注意：您必须指定 --db-path 参数，指向已解密的 MSG.db 文件。
如果您还没有解密的数据库文件，请先使用 WeChatMsg 主程序解密您的微信数据库。
"""

import argparse
import json
import os
import sqlite3
import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
import platform

def convert_to_timestamp(time_range):
    """将时间范围转换为时间戳"""
    start_time, end_time = time_range
    
    # 处理字符串类型的时间
    if isinstance(start_time, str):
        try:
            start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            start_time = datetime.strptime(start_time, "%Y-%m-%d")
    
    if isinstance(end_time, str):
        try:
            end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            end_time = datetime.strptime(end_time, "%Y-%m-%d")
    
    # 处理日期类型的时间
    if hasattr(start_time, 'timestamp'):
        start_time = int(start_time.timestamp())
    if hasattr(end_time, 'timestamp'):
        end_time = int(end_time.timestamp())
    
    return start_time, end_time


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


def get_all_messages(db_path, time_range=None):
    """
    从数据库获取指定时间范围内的所有消息
    
    Args:
        db_path: 数据库文件路径
        time_range: 时间范围元组 (开始时间, 结束时间)
    
    Returns:
        List: 消息列表
    """
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        return []
    
    if time_range:
        start_time, end_time = convert_to_timestamp(time_range)
    
    sql = f'''
        select localId,TalkerId,Type,SubType,IsSender,CreateTime,Status,StrContent,
        strftime('%Y-%m-%d %H:%M:%S',CreateTime,'unixepoch','localtime') as StrTime,
        MsgSvrID,BytesExtra,StrTalker,Reserved1,CompressContent
        from MSG
        {'WHERE CreateTime>' + str(start_time) + ' AND CreateTime<' + str(end_time) if time_range else ''}
        order by CreateTime
    '''
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f"查询数据库时出错: {str(e)}")
        return []


def get_contact_info(db_path, username):
    """
    获取联系人信息
    
    Args:
        db_path: 联系人数据库路径
        username: 联系人用户名
    
    Returns:
        Tuple: 联系人信息元组
    """
    if not os.path.exists(db_path):
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 尝试使用完整的SQL查询
            sql = '''
                SELECT UserName, Alias, Type, Remark, NickName, PYInitial, RemarkPYInitial, 
                ContactHeadImgUrl.smallHeadImgUrl, ContactHeadImgUrl.bigHeadImgUrl, ExTraBuf, 
                COALESCE(ContactLabel.LabelName, 'None') AS labelName
                FROM Contact
                INNER JOIN ContactHeadImgUrl ON Contact.UserName = ContactHeadImgUrl.usrName
                LEFT JOIN ContactLabel ON Contact.LabelIDList = ContactLabel.LabelId
                WHERE UserName = ?
            '''
            cursor.execute(sql, [username])
            result = cursor.fetchone()
        except sqlite3.OperationalError:
            # 如果ContactLabel表不存在，使用简化的SQL查询
            sql = '''
                SELECT UserName, Alias, Type, Remark, NickName, PYInitial, RemarkPYInitial, 
                ContactHeadImgUrl.smallHeadImgUrl, ContactHeadImgUrl.bigHeadImgUrl, ExTraBuf, "None"
                FROM Contact
                INNER JOIN ContactHeadImgUrl ON Contact.UserName = ContactHeadImgUrl.usrName
                WHERE UserName = ?
            '''
            cursor.execute(sql, [username])
            result = cursor.fetchone()
        
        conn.close()
        return result
    except Exception as e:
        print(f"获取联系人信息时出错: {str(e)}")
        return None


def format_message_for_json(message):
    """
    将消息记录格式化为适合JSON导出的格式
    
    Args:
        message: 原始消息记录元组
    
    Returns:
        Dict: 格式化后的消息字典
    """
    # 将BytesExtra转换为十六进制字符串，如果存在的话
    bytes_extra = None
    if message[10]:
        try:
            bytes_extra = message[10].hex()
        except:
            bytes_extra = None
    
    # 将CompressContent转换为十六进制字符串，如果存在的话
    compress_content = None
    if len(message) > 13 and message[13]:
        try:
            compress_content = message[13].hex()
        except:
            compress_content = None
    
    return {
        "message_id": message[0],
        "talker_id": message[1],
        "type": message[2],
        "sub_type": message[3],
        "is_sender": bool(message[4]),
        "timestamp": message[5],
        "formatted_time": message[8],
        "content": message[7],
        "msg_svr_id": message[9],
        "bytes_extra": bytes_extra,
        "talker": message[11],
        "reserved1": message[12] if len(message) > 12 else None,
        "compress_content": compress_content
    }


def export_chat_records(
        db_path, 
        contact_db_path, 
        time_range=None, 
        output_path=None
):
    """
    导出指定时间范围内的所有聊天记录到JSON文件
    
    Args:
        db_path: 消息数据库路径
        contact_db_path: 联系人数据库路径
        time_range: 时间范围元组 (开始时间, 结束时间)
        output_path: 输出文件路径，如果为None则自动生成
    
    Returns:
        str: 导出的JSON文件路径
    """
    # 获取所有消息
    all_messages = get_all_messages(db_path, time_range)
    if not all_messages:
        print("未找到指定时间范围内的聊天记录")
        return ""
    
    # 按联系人/群聊分组
    grouped_messages = {}
    for message in all_messages:
        # StrTalker在索引11的位置
        talker = message[11]
        if talker not in grouped_messages:
            grouped_messages[talker] = []
        grouped_messages[talker].append(message)
    
    # 获取联系人信息
    contacts_info = {}
    for talker in grouped_messages.keys():
        contact_info = get_contact_info(contact_db_path, talker)
        if contact_info:
            contacts_info[talker] = {
                "username": contact_info[0],
                "alias": contact_info[1],
                "type": contact_info[2],
                "remark": contact_info[3],
                "nickname": contact_info[4],
                "is_chatroom": "@chatroom" in contact_info[0]
            }
        else:
            # 如果找不到联系人信息，使用基本信息
            contacts_info[talker] = {
                "username": talker,
                "alias": "",
                "type": -1,
                "remark": "",
                "nickname": talker,
                "is_chatroom": "@chatroom" in talker
            }
    
    # 格式化消息记录
    formatted_data = {
        "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_range": {
            "start": datetime.fromtimestamp(convert_to_timestamp(time_range)[0]).strftime("%Y-%m-%d %H:%M:%S") if time_range else "all",
            "end": datetime.fromtimestamp(convert_to_timestamp(time_range)[1]).strftime("%Y-%m-%d %H:%M:%S") if time_range else "all"
        },
        "contacts": contacts_info,
        "messages": {}
    }
    
    # 格式化每个联系人/群聊的消息
    for talker, messages in grouped_messages.items():
        formatted_data["messages"][talker] = [format_message_for_json(msg) for msg in messages]
    
    # 生成输出文件路径
    if not output_path:
        start_time = "all"
        end_time = "all"
        if time_range:
            start_timestamp, end_timestamp = convert_to_timestamp(time_range)
            start_time = datetime.fromtimestamp(start_timestamp).strftime("%Y%m%d")
            end_time = datetime.fromtimestamp(end_timestamp).strftime("%Y%m%d")
        
        output_dir = os.path.join(os.getcwd(), "exports")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_path = os.path.join(output_dir, f"wechat_records_{start_time}_to_{end_time}.json")
    
    # 写入JSON文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)
        print(f"聊天记录已导出到: {output_path}")
        return output_path
    except Exception as e:
        print(f"导出聊天记录失败: {str(e)}")
        return ""


def show_help_message():
    """显示帮助信息"""
    print("""
=== 微信聊天记录导出工具使用指南 ===

此工具用于将微信聊天记录导出为JSON格式。您需要提供已解密的微信数据库文件。

1. 获取解密后的数据库文件:
   - 使用WeChatMsg主程序解密您的微信数据库
   - 解密后的文件通常位于 ./app/Database/Msg/ 目录下
   - 主要需要 MSG.db (消息数据库) 和 MicroMsg.db (联系人数据库)

2. 基本使用:
   python simple_export.py --db-path "path/to/MSG.db" --contact-db-path "path/to/MicroMsg.db"

3. 指定时间范围:
   python simple_export.py --db-path "path/to/MSG.db" --start "2023-01-01" --end "2023-12-31"

4. 指定输出文件:
   python simple_export.py --db-path "path/to/MSG.db" --output "my_export.json"

如果您不确定数据库文件的位置，请先运行WeChatMsg主程序并完成解密步骤。
""")


def get_documents_path():
    """获取用户文档目录路径"""
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            documents_path = winreg.QueryValueEx(key, "Personal")[0]
            return documents_path
        else:
            # 对于非Windows系统，使用HOME环境变量
            return os.path.join(os.environ['HOME'], 'Documents')
    except Exception as e:
        print(f"无法获取文档目录: {str(e)}")
        # 回退到用户主目录
        return os.path.expanduser("~")


def find_wechat_files():
    """查找微信数据库文件的可能位置"""
    possible_paths = []
    
    # 1. 标准的WeChatMsg解密后路径
    possible_paths.append("./app/Database/Msg")
    
    # 2. 基于用户文档目录的微信文件路径
    documents_path = get_documents_path()
    wechat_files_path = os.path.join(documents_path, "WeChat Files")
    
    # 遍历WeChat Files目录下的所有文件夹（通常是微信账号）
    if os.path.exists(wechat_files_path):
        try:
            for account_dir in os.listdir(wechat_files_path):
                account_path = os.path.join(wechat_files_path, account_dir)
                if os.path.isdir(account_path):
                    # 检查常见的数据库位置
                    msg_path = os.path.join(account_path, "Msg")
                    if os.path.exists(msg_path):
                        possible_paths.append(msg_path)
                    
                    # 检查FileStorage目录
                    file_storage = os.path.join(account_path, "FileStorage")
                    if os.path.exists(file_storage):
                        possible_paths.append(file_storage)
        except Exception as e:
            print(f"遍历WeChat Files目录时出错: {str(e)}")
    
    # 3. 添加其他可能的位置
    possible_paths.extend([
        "./Msg",
        "./data",
        "./data/Msg",
        os.path.join(os.getcwd(), "Msg"),
        os.path.join(os.path.expanduser("~"), "WeChat Files")
    ])
    
    return possible_paths


def find_db_files():
    """查找MSG.db和MicroMsg.db文件"""
    msg_db_paths = []
    contact_db_paths = []
    
    possible_dirs = find_wechat_files()
    
    for dir_path in possible_dirs:
        if not os.path.exists(dir_path):
            continue
        
        # 直接检查目录中是否有数据库文件
        msg_db = os.path.join(dir_path, "MSG.db")
        if os.path.exists(msg_db):
            msg_db_paths.append(msg_db)
        
        micro_msg_db = os.path.join(dir_path, "MicroMsg.db")
        if os.path.exists(micro_msg_db):
            contact_db_paths.append(micro_msg_db)
        
        # 检查子目录
        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isdir(item_path):
                    # 检查子目录中的数据库文件
                    sub_msg_db = os.path.join(item_path, "MSG.db")
                    if os.path.exists(sub_msg_db):
                        msg_db_paths.append(sub_msg_db)
                    
                    sub_micro_msg_db = os.path.join(item_path, "MicroMsg.db")
                    if os.path.exists(sub_micro_msg_db):
                        contact_db_paths.append(sub_micro_msg_db)
        except Exception as e:
            # 忽略权限错误等
            pass
    
    return msg_db_paths, contact_db_paths


def main():
    parser = argparse.ArgumentParser(description="导出微信聊天记录到JSON文件")
    parser.add_argument("--db-path", help="消息数据库路径 (MSG.db)")
    parser.add_argument("--contact-db-path", help="联系人数据库路径 (MicroMsg.db)")
    parser.add_argument("--start", help="开始时间 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--end", help="结束时间 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--help-more", action="store_true", help="显示更多帮助信息")
    parser.add_argument("--list-db", action="store_true", help="列出找到的所有数据库文件")
    
    args = parser.parse_args()
    
    if args.help_more:
        show_help_message()
        sys.exit(0)
    
    # 查找数据库文件
    msg_db_paths, contact_db_paths = find_db_files()
    
    # 如果指定了--list-db参数，列出所有找到的数据库文件
    if args.list_db:
        print("\n=== 找到的消息数据库文件 ===")
        for i, path in enumerate(msg_db_paths):
            print(f"{i+1}. {path}")
        
        print("\n=== 找到的联系人数据库文件 ===")
        for i, path in enumerate(contact_db_paths):
            print(f"{i+1}. {path}")
        
        print("\n使用示例:")
        if msg_db_paths and contact_db_paths:
            print(f'python simple_export.py --db-path "{msg_db_paths[0]}" --contact-db-path "{contact_db_paths[0]}"')
        sys.exit(0)
    
    # 尝试查找数据库文件
    if not args.db_path:
        # 使用找到的第一个MSG.db文件
        if msg_db_paths:
            args.db_path = msg_db_paths[0]
            print(f"找到消息数据库: {args.db_path}")
        else:
            print("错误: 未找到消息数据库文件。请使用 --db-path 参数指定 MSG.db 文件的位置。")
            print("提示: 您需要先使用WeChatMsg主程序解密您的微信数据库，或者使用 --list-db 参数查看可用的数据库文件。")
            print("运行 'python simple_export.py --help-more' 获取更多帮助信息。")
            sys.exit(1)
    
    if not args.contact_db_path:
        # 使用找到的第一个MicroMsg.db文件
        if contact_db_paths:
            args.contact_db_path = contact_db_paths[0]
            print(f"找到联系人数据库: {args.contact_db_path}")
        else:
            print("警告: 未找到联系人数据库文件。将无法获取联系人详细信息。")
            # 创建一个空的临时数据库文件
            args.contact_db_path = ":memory:"
    
    # 解析时间范围
    time_range = None
    if args.start or args.end:
        start_time = parse_date(args.start) if args.start else datetime(1970, 1, 1)
        end_time = parse_date(args.end) if args.end else datetime.now()
        time_range = (start_time, end_time)
    
    # 导出聊天记录
    try:
        export_chat_records(args.db_path, args.contact_db_path, time_range, args.output)
    except Exception as e:
        print(f"导出过程中出错: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)
