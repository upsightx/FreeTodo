export type ContentType = 'video' | 'note';

export interface Content {
    id: string;
    url: string;
    title: string;
    content_type: ContentType;
    cover_url: string;
    image_urls?: string[];
    video_download_url: string;
    extria_info?: {
        media_format?: string;
        audio_url?: string;
        duration?: number;
        owner?: any;
        [key: string]: any;
    };
}

export interface CreatorContentListResponse {
    contents: Content[];
    has_more: boolean;
    next_cursor: string;
}

export interface ContentListResponse {
    biz_code: number;
    msg: string;
    isok: boolean;
    data: CreatorContentListResponse;
}

export interface ContentDetailResponse {
    biz_code: number;
    msg: string;
    isok: boolean;
    data: {
        content: Content;
    };
} 