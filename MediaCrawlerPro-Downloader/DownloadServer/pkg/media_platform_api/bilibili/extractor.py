from ast import main
import json
import re
import logging
from typing import Dict, List, Optional
import urllib.parse

from constant.bilibili import BILI_INDEX_URL
from models.base_model import ContentTypeEnum
from models.content_detail import Content, ContentDetailResponse
from models.creator import CreatorContentListResponse, CreatorQueryResponse

logger = logging.getLogger(__name__)


class BiliExtractor:

    def extract_creator_info(
        self, up_info: Dict, relation_state: Dict, space_navnum: Dict
    ) -> Optional[CreatorQueryResponse]:
        """
        提取B站主页信息

        Args:
            up_info (Dict): B站用户信息
            relation_state (Dict): B站用户关系状态
            space_navnum (Dict): B站用户空间导航栏数据

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        logger.debug(up_info, relation_state, space_navnum)
        if not up_info or not relation_state or not space_navnum:
            return None

        res_creator = CreatorQueryResponse(
            nickname=up_info.get("name", ""),
            avatar=up_info.get("face", ""),
            description=up_info.get("sign", ""),
            user_id=str(up_info.get("mid", "")),
            follower_count=str(relation_state.get("follower", "0")),
            following_count=str(relation_state.get("following", "0")),
            content_count=str(space_navnum.get("video", "0")),
        )
        return res_creator

    def extract_w_webid(self, html: str) -> str:
        """
        提取w_webid

        Args:
            html (str): B站主页HTML

        Returns:
            str: w_webid
        """
        __RENDER_DATA__ = re.search(
            r"<script id=\"__RENDER_DATA__\" type=\"application/json\">(.*?)</script>",
            html,
            re.S,
        ).group(1)
        w_webid = json.loads(urllib.parse.unquote(__RENDER_DATA__))["access_id"]
        return w_webid

    def extract_creator_contents(
        self, current_cursor: int, videos_res: Dict
    ) -> List[Content]:
        """
        提取创作者内容

        Args:
            current_cursor (int): 当前页码
            videos_res (Dict): B站创作者内容列表

        Returns:
            CreatorContentListResponse: 创作者内容列表
        """
        video_list = videos_res.get("list", {}).get("vlist", [])
        next_cursor = str(videos_res.get("page").get("pn") + 1)
        has_more = videos_res.get("page").get("count") > current_cursor * 30
        contents: List[Content] = []
        for video in video_list:
            contents.append(
                Content(
                    id=str(video.get("bvid", "")),
                    url=f"{BILI_INDEX_URL}/video/{video.get('bvid', '')}",
                    title=video.get("title", ""),
                    content_type=ContentTypeEnum.VIDEO,
                    cover_url=video.get("pic", ""),
                    image_urls=[],
                    video_download_url="",
                )
            )
        return CreatorContentListResponse(
            contents=contents, has_more=has_more, next_cursor=next_cursor
        )
