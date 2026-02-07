export interface CreatorInfo {
  nickname: string;
  avatar: string;
  description: string;
  user_id: string;
  follower_count: string;
  following_count: string;
  content_count: string;
}

export interface CreatorInfoResponse {
    isok: boolean; 
    msg: string;
    data: CreatorInfo;
}