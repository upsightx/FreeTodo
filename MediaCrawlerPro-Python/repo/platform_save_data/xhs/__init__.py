# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-Python project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-Python/blob/main/repo/platform_save_data/xhs/__init__.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 17:34
# @Desc    :
import json
from typing import Dict, List

import config
from base.base_crawler import AbstractStore
from model.m_xhs import XhsComment, XhsCreator, XhsNote
from pkg.tools import utils
from repo.platform_save_data.xhs.xhs_store_impl import (
    XhsCsvStoreImplement,
    XhsDbStoreImplement,
    XhsJsonStoreImplement,
)
from var import source_keyword_var


# 用于缓存已存在的 note_id 集合（CSV 模式）
_csv_note_ids_cache: set = set()
_csv_cache_loaded: bool = False


def _load_csv_note_ids() -> set:
    """
    从 CSV 文件中加载所有已存在的 note_id
    
    Returns:
        set: 已存在的 note_id 集合
    """
    import os
    import csv
    
    global _csv_note_ids_cache, _csv_cache_loaded
    
    if _csv_cache_loaded:
        return _csv_note_ids_cache
    
    csv_store_path = "data/xhs"
    note_ids = set()
    
    if not os.path.exists(csv_store_path):
        _csv_cache_loaded = True
        return note_ids
    
    # 遍历所有 CSV 文件，提取 note_id
    for filename in os.listdir(csv_store_path):
        if filename.endswith(".csv") and "contents" in filename:
            filepath = os.path.join(csv_store_path, filename)
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if "note_id" in row and row["note_id"]:
                            note_ids.add(row["note_id"])
            except Exception as e:
                utils.logger.warning(f"[check_note_exists] Failed to read CSV file {filepath}: {e}")
    
    _csv_note_ids_cache = note_ids
    _csv_cache_loaded = True
    utils.logger.info(f"[check_note_exists] Loaded {len(note_ids)} existing note_ids from CSV files")
    return note_ids


def add_note_id_to_csv_cache(note_id: str) -> None:
    """
    将新爬取的 note_id 添加到缓存中
    
    Args:
        note_id: 帖子ID
    """
    global _csv_note_ids_cache
    _csv_note_ids_cache.add(note_id)


async def check_note_exists(note_id: str) -> bool:
    """
    检查帖子是否已存在
    支持 db 和 csv 两种存储模式
    
    Args:
        note_id: 帖子ID
        
    Returns:
        bool: 如果帖子存在返回 True，否则返回 False
    """
    if config.SAVE_DATA_OPTION == "db":
        from .xhs_store_sql import query_content_by_content_id
        note_detail: Dict = await query_content_by_content_id(content_id=note_id)
        return bool(note_detail)
    
    elif config.SAVE_DATA_OPTION == "csv":
        existing_ids = _load_csv_note_ids()
        return note_id in existing_ids
    
    else:
        # JSON 模式暂不支持，返回 False
        return False


class XhsStoreFactory:
    STORES = {
        "csv": XhsCsvStoreImplement,
        "db": XhsDbStoreImplement,
        "json": XhsJsonStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = XhsStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[XhsStoreFactory.create_store] Invalid save option only supported csv or db or json ..."
            )
        return store_class()


async def batch_update_xhs_notes(notes: List[XhsNote]):
    """
    批量更新小红书笔记
    Args:
        notes: 笔记列表
    """
    if not notes:
        return

    for note_item in notes:
        await update_xhs_note(note_item)


async def update_xhs_note(note_item: XhsNote):
    """
    更新小红书笔记
    Args:
        note_item: 笔记对象
    """
    note_item.source_keyword = source_keyword_var.get()
    local_db_item = note_item.model_dump()
    local_db_item.update({"last_modify_ts": utils.get_current_timestamp()})

    print_title = note_item.title[:30] or note_item.desc[:30]
    utils.logger.info(
        f"[store.xhs.update_xhs_note] xhs note, id: {note_item.note_id}, title: {print_title}"
    )
    await XhsStoreFactory.create_store().store_content(local_db_item)


async def batch_update_xhs_note_comments(comments: List[XhsComment]):
    """
    批量更新小红书笔记评论
    Args:
        comments: 评论列表
    """
    if not comments:
        return

    for comment_item in comments:
        await update_xhs_note_comment(comment_item)


async def update_xhs_note_comment(comment_item: XhsComment):
    """
    更新小红书笔记评论
    Args:
        comment_item: 评论对象
    """
    local_db_item = comment_item.model_dump()
    local_db_item.update({"last_modify_ts": utils.get_current_timestamp()})

    utils.logger.info(
        f"[store.xhs.update_xhs_note_comment] xhs note comment, note_id: {comment_item.note_id}, comment_id: {comment_item.comment_id}"
    )
    await XhsStoreFactory.create_store().store_comment(local_db_item)


async def save_creator(creator: XhsCreator):
    """
    保存小红书创作者信息
    Args:
        creator: 创作者对象
    """
    if not creator:
        return

    local_db_item = creator.model_dump()
    local_db_item.update({"last_modify_ts": utils.get_current_timestamp()})

    utils.logger.info(
        f"[store.xhs.save_creator] creator: {creator.user_id} - {creator.nickname}"
    )
    await XhsStoreFactory.create_store().store_creator(local_db_item)
