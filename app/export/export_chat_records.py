import json
import os
from datetime import datetime, date
from typing import Tuple, Dict, List, Union, Optional

from app.DataBase import msg_db, micro_msg_db
from app.DataBase.msg import convert_to_timestamp
from app.log import logger


def get_all_chat_records_by_time(
        time_range=None
) -> Dict:
    """
    获取指定时间范围内所有联系人和群聊的聊天记录
    
    Args:
        time_range: 时间范围元组 (开始时间, 结束时间)，时间可以是时间戳、字符串或日期对象
    
    Returns:
        Dict: 以联系人/群聊的wxid为键，聊天记录列表为值的字典
    """
    # 获取所有消息
    all_messages = msg_db.get_messages_all(time_range)
    if not all_messages:
        return {}
    
    # 按联系人/群聊分组
    grouped_messages = {}
    for message in all_messages:
        # StrTalker在索引11的位置
        talker = message[11]
        if talker not in grouped_messages:
            grouped_messages[talker] = []
        grouped_messages[talker].append(message)
    
    return grouped_messages


def _format_message_for_json(message) -> Dict:
    """
    将消息记录格式化为适合JSON导出的格式
    
    Args:
        message: 原始消息记录元组
    
    Returns:
        Dict: 格式化后的消息字典
    """
    # 消息字段定义
    # localId(0), TalkerId(1), Type(2), SubType(3), IsSender(4), CreateTime(5), 
    # Status(6), StrContent(7), StrTime(8), MsgSvrID(9), BytesExtra(10), 
    # StrTalker(11), Reserved1(12), CompressContent(13)
    
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


def export_chat_records_to_json(
        time_range=None,
        output_path=None
) -> str:
    """
    导出指定时间范围内的所有聊天记录到JSON文件
    
    Args:
        time_range: 时间范围元组 (开始时间, 结束时间)，时间可以是时间戳、字符串或日期对象
        output_path: 输出文件路径，如果为None则自动生成
    
    Returns:
        str: 导出的JSON文件路径
    """
    # 获取所有聊天记录
    grouped_messages = get_all_chat_records_by_time(time_range)
    if not grouped_messages:
        logger.warning("未找到指定时间范围内的聊天记录")
        return ""
    
    # 获取联系人信息
    contacts_info = {}
    for talker in grouped_messages.keys():
        contact_info = micro_msg_db.get_contact_by_username(talker)
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
        formatted_data["messages"][talker] = [_format_message_for_json(msg) for msg in messages]
    
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
        logger.info(f"聊天记录已导出到: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"导出聊天记录失败: {str(e)}")
        return ""


if __name__ == "__main__":
    # 示例：导出过去一天的聊天记录
    from datetime import datetime, timedelta
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)
    
    export_path = export_chat_records_to_json((start_time, end_time))
    print(f"聊天记录已导出到: {export_path}")
