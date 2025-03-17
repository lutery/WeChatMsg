# -*- coding: utf-8 -*-
"""
@File    : __init__.py
@Time    : 2025/03/15
@comment : Export functionality for WeChat messages
"""

from .export_chat_records import export_chat_records_to_json, get_all_chat_records_by_time

__all__ = ['export_chat_records_to_json', 'get_all_chat_records_by_time']
