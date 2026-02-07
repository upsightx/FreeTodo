export interface VideoProgress {
    id: string;
    title: string;
    progress: number;
}

export interface DownloadResponse {
    total_videos: number;
    videoProgress: VideoProgress[];
}

export interface ProgressResponse {
    total_videos: number;
    videoProgress: VideoProgress[];
}
