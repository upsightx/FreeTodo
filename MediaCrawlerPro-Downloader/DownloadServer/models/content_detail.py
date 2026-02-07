from typing import List, Optional, Dict

from pydantic import BaseModel, Field

from models.base_model import ContentTypeEnum, PlatformEnum


class Content(BaseModel):
    """
    内容
    """

    id: str = Field(title="内容ID", description="内容ID")
    url: str = Field(title="内容URL", description="内容URL")
    title: str = Field(title="内容标题", description="内容标题")
    content_type: ContentTypeEnum = Field(title="内容类型", description="内容类型")
    cover_url: str = Field(title="封面URL", description="封面URL")
    image_urls: Optional[List[str]] = Field(
        title="图片URL列表", description="图片URL列表"
    )
    video_download_url: str = Field(title="视频下载URL", description="视频下载URL")
    extria_info: Optional[Dict] = Field(
        title="额外信息", default=None, description="存放视频额外的信息"
    )


class ContentDetailRequest(BaseModel):
    """
    内容详情请求
    """

    platform: PlatformEnum = Field(..., title="平台", description="平台")
    content_url: str = Field(..., title="内容URL", description="内容URL")
    cookies: str = Field(
        ..., title="登录成功后的cookies", description="登录成功后的cookies"
    )


class ContentDetailResponse(BaseModel):
    """
    内容详情响应
    """

    content: Content = Field(..., title="内容", description="内容")
