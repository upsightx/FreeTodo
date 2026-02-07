# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-Python project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-Python/blob/main/repo/platform_save_data/bilibili/__init__.py
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
# @Time    : 2024/1/14 19:34
# @Desc    :

from typing import List

import config
from model.m_bilibili import BilibiliVideo, BilibiliComment, BilibiliUpInfo, CreatorQueryResponse
from pkg.tools import utils
from var import source_keyword_var

from .bilibili_store_impl import *


# 用于缓存已存在的 video_id (bvid) 集合（CSV 模式）
_csv_video_ids_cache: set = set()
_csv_cache_loaded: bool = False


def _load_csv_video_ids() -> set:
    """
    从 CSV 文件中加载所有已存在的 video_id (bvid)
    
    Returns:
        set: 已存在的 video_id 集合
    """
    import os
    import csv
    
    global _csv_video_ids_cache, _csv_cache_loaded
    
    if _csv_cache_loaded:
        return _csv_video_ids_cache
    
    csv_store_path = "data/bilibili"
    video_ids = set()
    
    if not os.path.exists(csv_store_path):
        _csv_cache_loaded = True
        return video_ids
    
    # 遍历所有 CSV 文件，提取 bvid
    for filename in os.listdir(csv_store_path):
        if filename.endswith(".csv") and "contents" in filename:
            filepath = os.path.join(csv_store_path, filename)
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if "bvid" in row and row["bvid"]:
                            video_ids.add(row["bvid"])
            except Exception as e:
                utils.logger.warning(f"[check_video_exists] Failed to read CSV file {filepath}: {e}")
    
    _csv_video_ids_cache = video_ids
    _csv_cache_loaded = True
    utils.logger.info(f"[check_video_exists] Loaded {len(video_ids)} existing video_ids from CSV files")
    return video_ids


def add_video_id_to_csv_cache(video_id: str) -> None:
    """
    将新爬取的 video_id (bvid) 添加到缓存中
    
    Args:
        video_id: 视频ID (bvid)
    """
    global _csv_video_ids_cache
    _csv_video_ids_cache.add(video_id)


async def check_video_exists(bvid: str) -> bool:
    """
    检查视频是否已存在
    支持 db 和 csv 两种存储模式
    
    Args:
        bvid: 视频ID (bvid)
        
    Returns:
        bool: 如果视频存在返回 True，否则返回 False
    """
    if config.SAVE_DATA_OPTION == "db":
        from .bilibili_store_sql import query_content_by_bvid
        video_detail = await query_content_by_bvid(bvid=bvid)
        return bool(video_detail)
    
    elif config.SAVE_DATA_OPTION == "csv":
        existing_ids = _load_csv_video_ids()
        return bvid in existing_ids
    
    else:
        # JSON 模式暂不支持，返回 False
        return False


class BiliStoreFactory:
    STORES = {
        "csv": BiliCsvStoreImplement,
        "db": BiliDbStoreImplement,
        "json": BiliJsonStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = BiliStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[BiliStoreFactory.create_store] Invalid save option only supported csv or db or json ..."
            )
        return store_class()


async def update_bilibili_creator(creator_info: CreatorQueryResponse):
    utils.logger.info(
        f"[store.bilibili.update_bilibili_creator] bilibili creator info: {creator_info}"
    )

    save_data = creator_info.model_dump()
    save_data["last_modify_ts"] = utils.get_current_timestamp()
    await BiliStoreFactory.create_store().store_creator(save_data)


async def update_bilibili_up_info(up_info: BilibiliUpInfo):
    utils.logger.info(
        f"[store.bilibili.update_bilibili_up_info] bilibili up info: user_id={up_info.user_id}, nickname={up_info.nickname}"
    )

    save_data = up_info.model_dump()
    save_data["last_modify_ts"] = utils.get_current_timestamp()
    # Convert string fields to int for database bigint columns
    save_data["follower_count"] = int(save_data.get("follower_count", "0") or "0")
    save_data["following_count"] = int(save_data.get("following_count", "0") or "0")
    save_data["content_count"] = int(save_data.get("content_count", "0") or "0")
    await BiliStoreFactory.create_store().store_creator(save_data)


async def update_bilibili_video(video_item: BilibiliVideo):
    utils.logger.info(
        f"[store.bilibili.update_bilibili_video] bilibili bvid: {video_item.bvid}, title:{video_item.title[:100]}"
    )

    save_content_item = video_item.model_dump()
    save_content_item["last_modify_ts"] = utils.get_current_timestamp()
    await BiliStoreFactory.create_store().store_content(content_item=save_content_item)


async def update_up_info(up_info: BilibiliUpInfo):
    utils.logger.info(
        f"[store.bilibili.update_up_info] bilibili user_id:{up_info.user_id}"
    )

    save_up_info = up_info.model_dump()
    save_up_info["last_modify_ts"] = utils.get_current_timestamp()
    # Convert field types to match database
    save_up_info["follower_count"] = int(save_up_info.get("follower_count", "0") or "0")
    save_up_info["following_count"] = int(save_up_info.get("following_count", "0") or "0")
    save_up_info["content_count"] = int(save_up_info.get("content_count", "0") or "0")
    await BiliStoreFactory.create_store().store_creator(creator=save_up_info)


async def batch_update_bilibili_video_comments(video_id: str, comments: List[BilibiliComment]):
    if not comments:
        return
    for comment_item in comments:
        await update_bilibili_video_comment(comment_item)


async def update_bilibili_video_comment(comment_item: BilibiliComment):
    utils.logger.info(
        f"[store.bilibili.update_bilibili_video_comment] Bilibili video comment: {comment_item.comment_id}, content: {comment_item.content[:100]}"
    )

    save_comment_item = comment_item.model_dump()
    save_comment_item["last_modify_ts"] = utils.get_current_timestamp()
    await BiliStoreFactory.create_store().store_comment(comment_item=save_comment_item)
