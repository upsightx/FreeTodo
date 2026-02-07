<template>
  <div class="download-item">
    <div class="download-info">
      <div class="status-icon" :class="statusClass">
        <el-icon v-if="status === 'completed'" :size="16"><Check /></el-icon>
        <el-icon v-else-if="status === 'error'" :size="16"><Close /></el-icon>
        <el-icon v-else class="rotating" :size="16"><Loading /></el-icon>
      </div>
      <div class="download-details">
        <el-tooltip
          :content="filename"
          placement="top"
          :show-after="500"
          :hide-after="0"
        >
          <div class="filename">{{ truncatedFilename }}</div>
        </el-tooltip>
        <div class="status-text" :class="statusClass">{{ statusText }}</div>
      </div>
    </div>
    <el-progress
      :percentage="progress"
      :status="progressStatus"
      :format="formatProgress"
      :stroke-width="8"
      class="progress-bar"
      :show-text="true"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Check, Close, Loading } from "@element-plus/icons-vue";

const props = defineProps<{
  filename: string;
  progress: number;
  status: string;
  totalBytes: number;
  receivedBytes: number;
}>();

const statusText = computed(() => {
  switch (props.status) {
    case "downloading":
      return "下载中...";
    case "completed":
      return "下载完成";
    case "error":
      return "下载失败";
    case "cancelled":
      return "已取消";
    case "pending":
      return "等待中...";
    default:
      return "准备中...";
  }
});

const statusClass = computed(() => ({
  "status-completed": props.status === "completed",
  "status-error": props.status === "error",
  "status-downloading": props.status === "downloading",
  "status-cancelled": props.status === "cancelled",
  "status-pending": props.status === "pending",
}));

const progressStatus = computed(() => {
  switch (props.status) {
    case "completed":
      return "success";
    case "error":
      return "exception";
    default:
      return "";
  }
});

const formatProgress = (percentage: number) => {
  if (props.status === 'pending') {
    return '等待中...';
  }
  if (props.status === 'cancelled') {
    return '已取消';
  }
  if (props.status === 'error') {
    return '下载失败';
  }
  if (props.totalBytes === 0) {
    return `${percentage.toFixed(1)}%`;
  }
  const receivedMB = (props.receivedBytes / 1024 / 1024).toFixed(1);
  const totalMB = (props.totalBytes / 1024 / 1024).toFixed(1);
  return `${receivedMB}/${totalMB}MB`;
};

const truncatedFilename = computed(() => {
  const maxLength = 20;
  if (props.filename.length <= maxLength) {
    return props.filename;
  }
  return props.filename.slice(0, maxLength) + "...";
});
</script>

<style scoped>
.download-item {
  padding: 12px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.download-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 12px;
  width: 100%;
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(238, 238, 238, 0.15);
  flex-shrink: 0;
  font-size: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.status-completed {
  color: #00ffd1 !important;
  background: rgba(0, 173, 181, 0.3) !important;
  box-shadow: 0 0 10px rgba(0, 255, 209, 0.3);
}

.status-error {
  color: #ff6b6b !important;
  background: rgba(245, 108, 108, 0.3) !important;
  box-shadow: 0 0 10px rgba(255, 107, 107, 0.3);
}

.status-downloading {
  color: #00ffd1 !important;
  background: rgba(0, 173, 181, 0.2) !important;
  animation: pulse 2s infinite;
}

.status-cancelled {
  color: #909399 !important;
  background: rgba(144, 147, 153, 0.3) !important;
  box-shadow: 0 0 10px rgba(144, 147, 153, 0.3);
}

.status-pending {
  color: #e6a23c !important;
  background: rgba(230, 162, 60, 0.3) !important;
  animation: pulse 2s infinite;
}

.download-details {
  flex: 1;
  min-width: 0;
  text-align: center;
  max-width: calc(100% - 44px);
}

.filename {
  font-size: 13px;
  font-weight: 500;
  color: #eeeeee;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin: 0 auto;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  cursor: default;
  padding: 2px 0;
}

.status-text {
  font-size: 12px;
  color: #eeeeee;
  opacity: 0.9;
  margin-top: 4px;
  font-weight: 500;
}

.progress-bar {
  margin-top: 8px;
  width: 95%;
}

/* 自定义进度条样式 */
:deep(.el-progress-bar__outer) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-radius: 4px;
}

:deep(.el-progress-bar__inner) {
  background-image: linear-gradient(to right, #4f46e5, #00ffd1) !important;
  border-radius: 4px;
  transition: width 0.3s ease;
}

:deep(.el-progress.is-success .el-progress-bar__inner) {
  background-image: linear-gradient(to right, #00c9a7, #00ffd1) !important;
}

:deep(.el-progress.is-exception .el-progress-bar__inner) {
  background-image: linear-gradient(to right, #ff6b6b, #ff8585) !important;
}

:deep(.el-progress__text) {
  color: #eeeeee !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(0, 255, 209, 0.4);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(0, 255, 209, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(0, 255, 209, 0);
  }
}

:deep(.el-tooltip__popper) {
  max-width: 300px;
  font-size: 12px;
  line-height: 1.4;
  padding: 8px 12px;
}

:deep(.el-tooltip__popper .el-tooltip__content) {
  word-break: break-all;
  white-space: normal;
}
</style> 