import axios from 'axios'
import type { CreatorInfoResponse } from '../typings/creator';
import type { ContentListResponse, ContentDetailResponse } from '../typings/content';
import type { DownloadResponse, ProgressResponse } from '../typings/download';

// 从环境变量中获取
const BASE_URL = window.process?.env?.MEDIACRAWLER_PRO_DOWNLOADER_API_BASE_URL || 'http://localhost:8205';

const api = axios.create({
    baseURL: BASE_URL,
    timeout: 10000,
});

export interface CreatorQueryParams {
    platform: string;
    creator_url: string;
    cookies: string;
}

export interface CreatorContentParams {
    creator_id: string;
    cursor: string;
    cookies: string;
    platform: string;
}

export interface ContentDetailParams {
    platform: string;
    content_url: string;
    cookies: string;
}

export const apiService = {
    // 查询创作者信息
    async queryCreatorInfo(params: CreatorQueryParams): Promise<CreatorInfoResponse> {
        const response = await api.post<CreatorInfoResponse>('/api/v1/creator_query', params);
        return response.data;
    },

    // 获取创作者视频列表
    async getCreatorContents(params: CreatorContentParams): Promise<ContentListResponse> {
        const response = await api.post<ContentListResponse>('/api/v1/creator_contents', params);
        return response.data;
    },

    // 查询内容详情
    async queryContentDetail(params: ContentDetailParams): Promise<ContentDetailResponse> {
        const response = await api.post<ContentDetailResponse>('/api/v1/content_detail', params);
        return response.data;
    }
}; 