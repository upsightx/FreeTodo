# -*- coding: utf-8 -*-
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from logic.base_logic import BaseLogic
from models.base_model import PlatformEnum
from models.content_detail import ContentDetailRequest, ContentDetailResponse


class ContentDetailLogic(BaseLogic):

    def __init__(self, platform: PlatformEnum, cookies: str = ""):
        """
        content detail logic constructor

        Args:
            platform_name:
        """
        super().__init__(platform, cookies)

    async def async_initialize(self, **kwargs):
        """
        async initialize
        Returns:

        """
        await super().async_initialize(**kwargs)

    def extract_content_id(self, url: str) -> Tuple[bool, str, str]:
        """
        extract content id from url

        Args:
            url: media platform user url

        Returns:
            tuple:
                bool: is_valid
                str: extract_msg
                str: content_id
        """
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        url = parsed_url.netloc + parsed_url.path
        if url.endswith("/"):
            url = url[:-1]
        mutile_patterns: List[str] = []
        if self.platform == PlatformEnum.DOUYIN:
            if query_params and (
                query_params.get("aweme_id") or query_params.get("modal_id")
            ):
                return (
                    True,
                    "",
                    query_params.get("aweme_id", [None])[0]
                    or query_params.get("modal_id", [None])[0],
                )

            pattern_video = r"/video/(.*)"
            pattern_note = r"/note/(.*)"
            mutile_patterns.append(pattern_video)
            mutile_patterns.append(pattern_note)
        elif self.platform == PlatformEnum.XHS:
            pattern_video = r"/explore/(.*)"
            mutile_patterns.append(pattern_video)
        elif self.platform == PlatformEnum.BILIBILI:
            pattern_video = r"/video/(.*)"
            mutile_patterns.append(pattern_video)
        elif self.platform == PlatformEnum.KUAISHOU:
            # https://www.kuaishou.com/short-video/3xm56cbtcj4gsz4?authorId=3xe2y946ihptq99&streamSource=profile&area=profilexxnull
            pattern_video = r"/short-video/(.*)"
            mutile_patterns.append(pattern_video)
        else:
            return False, "无效的自媒体平台", ""

        for pattern in mutile_patterns:
            match = re.findall(pattern, url)
            if match:
                return True, "", match[0]
        else:
            return False, "无效的URL", ""

    async def query_content_detail(
        self, content_id: str, ori_content_url: str = ""
    ) -> Optional[ContentDetailResponse]:
        """
        查询内容详情

        Args:
            content_id (str): 内容ID

        Returns:
            ContentDetailResponse: 内容详情
        """
        return await self.api_client.get_content_detail(content_id, ori_content_url)
