export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  category: string;
  imageUrl: string;
  likes: number;
  comments: number;
  videoDuration?: string;
  source: string;
}

export interface BriefItem {
  id: string;
  content: string;
  tags: string[];
}
