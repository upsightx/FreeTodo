<template>
  <div class="creator-info-container" v-if="creatorInfo">
    <el-card class="creator-card">
      <div class="creator-content">
        <div class="creator-left">
          <div class="creator-avatar">
            <el-avatar
              :size="60"
              :src="creatorInfo.avatar"
              :alt="creatorInfo.nickname"
            />
          </div>
          <div class="creator-basic-info">
            <div class="creator-header">
              <h2 class="creator-name">{{ creatorInfo.nickname }}</h2>
              <el-tag size="small" type="info" class="creator-id-tag">
                ID: {{ creatorInfo.user_id }}
              </el-tag>
            </div>
            <div class="creator-stats">
              <div class="stat-item">
                <span class="stat-value">{{ creatorInfo.follower_count }}</span>
                <span class="stat-label">粉丝</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{
                  creatorInfo.following_count
                }}</span>
                <span class="stat-label">关注</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ creatorInfo.content_count }}</span>
                <span class="stat-label">作品</span>
              </div>
            </div>
          </div>
        </div>
        <!-- <div class="creator-description">
          <el-tag size="small" type="success" class="description-label"
            >签名</el-tag
          >
          <span class="description-text">{{
            creatorInfo.description || "这个人很懒，什么都没写~"
          }}</span>
        </div> -->
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import type { CreatorInfo } from "../typings/creator";

defineProps<{
  creatorInfo: CreatorInfo;
}>();
</script>

<style scoped>
.creator-info-container {
  margin-bottom: 20px;
}

.creator-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.creator-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.creator-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.creator-avatar :deep(.el-avatar) {
  border: 2px solid #6366f1;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);
}

.creator-basic-info {
  flex: 1;
}

.creator-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.creator-name {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.creator-id-tag {
  background: #f3f4f6;
  color: #6366f1;
  border: none;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 6px;
}

.creator-stats {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 12px;
  margin-top: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #6366f1;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
}

.stat-divider {
  width: 1px;
  height: 14px;
  background-color: #e4e7ed;
}

.creator-description {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.description-label {
  flex-shrink: 0;
  font-size: 12px;
  padding: 0 6px;
  height: 20px;
  line-height: 18px;
  background-color: #67c23a;
  color: white;
}

.description-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.4;
  flex-grow: 1;
  word-break: break-all;
}

/* Element Plus 标签样式覆盖 */
:deep(.el-tag) {
  border-radius: 3px;
}

:deep(.el-card) {
  border: none;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.el-button {
  background-color: #6366f1;
  border-color: #6366f1;
  border-radius: 8px;
}

.el-button:hover {
  background-color: #4f46e5;
  border-color: #4f46e5;
}
</style> 