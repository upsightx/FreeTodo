<template>
  <div class="video-list-container">
    <div class="video-list-header">
      <div class="selection-controls">
        <el-checkbox
          v-model="allSelected"
          @change="handleSelectAll"
          :indeterminate="isIndeterminate"
        >
          全选
        </el-checkbox>
        <span class="selected-count">
          已选择 {{ selectedVideos.length }} 个内容
        </span>
      </div>

      <div class="download-controls">
        <el-button
          type="primary"
          size="small"
          @click="handleDownload"
          :loading="isDownloading"
          :disabled="selectedVideos.length === 0"
        >
          {{ isDownloading ? "下载中..." : "下载选中内容" }}
        </el-button>
        
        <el-button
          type="warning"
          size="small"
          @click="selectFailedItems"
          :disabled="isDownloading || getFailedItems().length === 0"
          v-if="getFailedItems().length > 0"
        >
          选择失败项 ({{ getFailedItems().length }})
        </el-button>
      </div>
    </div>

    <div class="waterfall-wrapper" ref="scrollContainer" @scroll="handleScroll">
      <el-skeleton
        :loading="loading && contentList.length === 0"
        animated
        :count="8"
      >
        <template #template>
          <div class="waterfall-container" :class="`platform-${platform}`">
            <div v-for="i in 12" :key="i" class="skeleton-item">
              <div class="skeleton-image">
                <el-skeleton-item variant="image" style="width: 100%; height: 100%" />
              </div>
              <div class="skeleton-content">
                <el-skeleton-item variant="text" style="width: 60%; height: 16px" />
              </div>
              <div class="skeleton-badge">
                <el-skeleton-item variant="text" style="width: 40px; height: 20px" />
              </div>
              <div class="skeleton-checkbox">
                <el-skeleton-item variant="circle" style="width: 20px; height: 20px" />
              </div>
            </div>
          </div>
        </template>

        <template #default>
          <div class="waterfall-container" :class="`platform-${platform}`">
            <div
              v-for="video in contentList"
              :key="video.id"
              class="video-item"
              :class="{ selected: selectedVideos.includes(video.id) }"
              @click="
                handleSelect(video.id, !selectedVideos.includes(video.id))
              "
            >
              <div class="video-cover">
                <el-image
                  :src="getProxyImageUrl(video.cover_url, platform)"
                  :alt="video.title"
                  @load="handleImageLoad($event, video.id)"
                  @error="handleImageError($event, video.id, video.cover_url)"
                  fit="cover"
                  lazy
                >
                  <template #placeholder>
                    <div class="image-placeholder">
                      <el-skeleton-item
                        variant="image"
                        style="width: 100%; height: 100%"
                      />
                    </div>
                  </template>
                  <template #error>
                    <div class="image-error" :class="platform === 'bili' ? 'bili-error' : ''">
                      <el-icon v-if="platform === 'bili'"><VideoCamera /></el-icon>
                      <el-icon v-else><Picture /></el-icon>
                      <div v-if="platform === 'bili'" class="error-text">B站视频</div>
                    </div>
                  </template>
                </el-image>
                <div class="video-select">
                  <el-checkbox
                    :model-value="selectedVideos.includes(video.id)"
                    @change="(val) => handleSelect(video.id, val)"
                    @click.stop
                  />
                </div>
                <div class="video-info">
                  <h3>{{ video.title }}</h3>
                </div>
                <div
                  class="download-progress"
                  v-if="downloadProgress[video.id]"
                  :class="{
                    'download-completed':
                      downloadProgress[video.id].status === 'completed',
                    'download-error':
                      downloadProgress[video.id].status === 'error',
                    'download-cancelled':
                      downloadProgress[video.id].status === 'cancelled',
                    'download-pending':
                      downloadProgress[video.id].status === 'pending',
                  }"
                >
                  <DownloadItem
                    :filename="video.title"
                    :progress="downloadProgress[video.id].progress"
                    :status="downloadProgress[video.id].status"
                    :total-bytes="downloadProgress[video.id].totalBytes"
                    :received-bytes="downloadProgress[video.id].receivedBytes"
                  />
                </div>
                <div class="content-type-badge" :class="video.content_type">
                    <el-icon  v-if="video.content_type === 'video'"><VideoCamera /></el-icon>
                    <el-icon v-else><Picture /></el-icon>
                    {{ video.content_type === 'video' ? '视频' : '图文' }}        
                </div>
              </div>
            </div>
          </div>
        </template>
      </el-skeleton>

      <div v-if="loading && contentList.length > 0" class="loading-more">
        <el-icon class="loading-icon" :size="24"><Loading /></el-icon>
        <span>加载中...</span>
      </div>

      <div v-if="!hasMore && contentList.length > 0" class="no-more">
        没有更多数据了
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import type { Content } from "../typings/content";
import axios from "axios";
import { ElMessage } from "element-plus";
import { Loading, VideoCamera, Picture } from "@element-plus/icons-vue";
import { apiService } from "../api";
import DownloadItem from "./DownloadItem.vue";

const props = defineProps<{
  creatorId?: string;
  cookies: string;
  platform: string;
  contentList?: Content[];
}>();

const emit = defineEmits(["select-videos", "download-videos"]);

const contentList = ref<Content[]>(props.contentList || []);
const selectedVideos = ref<string[]>([]);
const hasMore = ref(false);
const nextCursor = ref("");
const loading = ref(false);
const errorMessage = ref("");

const allSelected = ref(false);
const isIndeterminate = ref(false);

watch(selectedVideos, (newVal) => {
  emit("select-videos", newVal);
});

const handleImageLoad = (event: Event, videoId: string) => {
  console.log(`Image loaded for video ${videoId}`);
};

const handleImageError = (event: Event, videoId: string, imageUrl: string) => {
  console.error(`Image failed to load for video ${videoId}, URL: ${imageUrl}`);
};


// B站图片代理URL处理
const getProxyImageUrl = (originalUrl: string, platform: string): string => {
  if (platform === 'bili' && originalUrl) {
    // 对于B站图片，我们可以尝试使用一些公共的图片代理服务
    // 或者直接使用原URL（如果Electron的webSecurity设置允许的话）
    return originalUrl;
  }
  return originalUrl;
};

const handleSelectAll = (val: boolean) => {
  if (val) {
    selectedVideos.value = contentList.value.map((video) => video.id);
  } else {
    selectedVideos.value = [];
  }
  allSelected.value = val;
};

const handleSelect = (videoId: string, checked: boolean) => {
  if (checked === selectedVideos.value.includes(videoId)) {
    return;
  }

  if (checked) {
    selectedVideos.value.push(videoId);
  } else {
    selectedVideos.value = selectedVideos.value.filter((id) => id !== videoId);
  }

  const checkedCount = selectedVideos.value.length;
  const newAllSelected = checkedCount === contentList.value.length;
  allSelected.value = newAllSelected;
  isIndeterminate.value =
    checkedCount > 0 && checkedCount < contentList.value.length;
};

const fetchVideos = async () => {
  if (!props.creatorId) return;
  
  try {
    loading.value = true;
    errorMessage.value = "";

    const response = await apiService.getCreatorContents({
      creator_id: props.creatorId,
      cursor: nextCursor.value,
      cookies: props.cookies,
      platform: props.platform,
    });

    if (response.isok) {
      const { contents, has_more, next_cursor } = response.data;
      if (!nextCursor.value) {
        contentList.value = contents;
      } else {
        contentList.value.push(...contents);
      }
      hasMore.value = has_more;
      nextCursor.value = next_cursor;
    } else {
      errorMessage.value = response.msg || "获取内容列表失败";
      ElMessage.error(errorMessage.value);
    }
  } catch (error) {
    console.error("获取内容列表失:", error);
    handleApiError(error);
  } finally {
    loading.value = false;
  }
};

const handleApiError = (error: unknown) => {
  console.log(error);
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNREFUSED") {
      errorMessage.value = "无法连接到服务器，请确保服务器已启动";
    } else if (error.response) {
      errorMessage.value = `获取内容列表失败: ${
        error.response.data.msg || "未知错误"
      }`;
    } else {
      errorMessage.value = "网络连接失败，请确认相关的服务是否启动";
    }
  } else {
    errorMessage.value = "获取内容列表失败，请稍后重试";
  }
  ElMessage.error(errorMessage.value);
};

const scrollContainer = ref<HTMLElement | null>(null);
const loadingMore = ref(false);

const handleScroll = async () => {
  if (
    !scrollContainer.value ||
    loading.value ||
    !hasMore.value ||
    loadingMore.value
  ) {
    return;
  }

  const container = scrollContainer.value;
  const scrollBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight;

  if (scrollBottom < 100) {
    loadingMore.value = true;
    try {
      await fetchVideos();
    } finally {
      loadingMore.value = false;
    }
  }
};

const isDownloading = ref(false);
const downloadingTasks = ref(new Set<string>());

const clearDownloadProgress = () => {
  downloadProgress.value = {};
  downloadingTasks.value.clear();
};

// 添加获取文件扩展名的辅助函数
const getFileExtension = async (url: string, defaultExt: string): Promise<string> => {
  try {
    // 先尝试从URL中获取扩展名
    const urlExt = url.split('?')[0].split('.').pop()?.toLowerCase();
    if (urlExt && ['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm'].includes(urlExt)) {
      return urlExt;
    }

    // 如果URL中没有有效的扩展名，尝试通过HEAD请求获取Content-Type
    const response = await axios.head(url);
    const contentType = response.headers['content-type'];
    
    if (contentType) {
      const mimeToExt: Record<string, string> = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp',
        'video/mp4': 'mp4',
        'video/webm': 'webm',
        'video/quicktime': 'mp4'
      };
      
      for (const [mime, ext] of Object.entries(mimeToExt)) {
        if (contentType.includes(mime)) {
          return ext;
        }
      }
    }
    
    // 如果都无法确定，返回默认扩展名
    return defaultExt;
  } catch (error) {
    console.error('获取文件扩展名失败:', error);
    return defaultExt;
  }
};

// 修改下载处理函数
const handleDownload = async () => {
  if (selectedVideos.value.length === 0) {
    ElMessage.warning("请先选择要下载的内容");
    return;
  }

  try {
    isDownloading.value = true;
    const result = await window.electronAPI.openDirectory();
    if (!result.filePaths || result.filePaths.length === 0) {
      isDownloading.value = false;
      return;
    }

    const saveDir = result.filePaths[0];
    const selectedContents = contentList.value.filter((content) =>
      selectedVideos.value.includes(content.id)
    );

    clearDownloadProgress();

    // 为每个选中的内容添加到待下载任务集合
    for (const content of selectedContents) {
      downloadingTasks.value.add(content.id);
    }

    for (const content of selectedContents) {
      try {
        // xhs的内容需要单独处理，在创作者模式下，接口返回的时候是没有具体的视频下载地址的，图片也是这是一个封面图
        // 这里需要单独处理成去查询内容详情，这么做的原因是如果在查询创作者列表的时候就直接批量拉xhs帖子详情很有可能失败，这个接口风控很严重。
        if (props.platform === "xhs") {
            // 查询单个内容详情
          const response = await apiService.queryContentDetail({
            platform: props.platform,
            content_url: content.url,
            cookies: props.cookies,
          });

          if (!response.isok) {
            ElMessage.error(`查询小红书帖子:${content.title}详情失败，跳过下载`);
            // 从待下载任务中移除
            downloadingTasks.value.delete(content.id);
            continue;
          }
          content.video_download_url = response.data.content.video_download_url;
          content.image_urls = response.data.content.image_urls;
        }

        if (content.content_type === 'video') {
          // 处理视频下载
          const videoExt = await getFileExtension(content.video_download_url, 'mp4');
          const sanitizedTitle = content.title
            .replace(/[\\/:*?"<>|]/g, "_")
            .replace(/\s+/g, "_")
            .replace(/_+/g, "_")
            .replace(/#/g, "")
            .slice(0, 50);
          
          emit("download-videos", {
            ContentList: [{
              ...content,
              video_download_url: content.video_download_url
            }],
            saveDir: saveDir,
          });
        } else if (content.content_type === 'note' && content.image_urls?.length) {
          // 处理图文内容的图片下载
          const totalImages = content.image_urls.length;
          let downloadedImages = 0;

          // 为整个图文内容创建一下载进度记录
          downloadProgress.value[content.id] = {
            progress: 0,
            status: 'downloading',
            totalBytes: 0,
            receivedBytes: 0,
          };

          for (let i = 0; i < content.image_urls.length; i++) {
            const imageUrl = content.image_urls[i];
            const imageExt = await getFileExtension(imageUrl, 'jpg');
            
            const sanitizedTitle = content.title
              .replace(/[\\/:*?"<>|]/g, "_")
              .replace(/\s+/g, "_")
              .replace(/_+/g, "_")
              .replace(/#/g, "")
              .slice(0, 50);
            
            const filename = content.image_urls.length > 1
              ? `${sanitizedTitle || content.id}_${i + 1}.${imageExt}`
              : `${sanitizedTitle || content.id}.${imageExt}`;

            // 使用单独的ID来跟踪每个图片的下载，但更新整体进度
            const imageDownloadId = `${content.id}_${i}`;
            
            try {
              console.log(props.platform, imageDownloadId, imageUrl, filename, saveDir, content.id);
              await window.electronAPI.startDownload(
                props.platform,
                imageDownloadId,
                imageUrl,
                filename,
                saveDir,
                content.id
              );

              // 更新已下载图片数量和总进度
              downloadedImages++;
              downloadProgress.value[content.id].progress = (downloadedImages / totalImages) * 100;
              
              if (downloadedImages === totalImages) {
                downloadProgress.value[content.id].status = 'completed';
              }
            } catch (error) {
              console.error(`下载图片失败: ${error}`);
              downloadProgress.value[content.id].status = 'error';
              downloadProgress.value[content.id].error = `下载图片失败: ${error}`;
              break;
            }
          }
        }
      } catch (error) {
        console.error(`处理内容 ${content.id} 失败:`, error);
        ElMessage.error(`处理内容 "${content.title}" 失败`);
        
        // 更新下载状态为错误
        if (downloadProgress.value[content.id]) {
          downloadProgress.value[content.id].status = 'error';
          downloadProgress.value[content.id].error = `下载失败: ${error}`;
        }
        
        // 从待下载任务中移除失败的任务
        downloadingTasks.value.delete(content.id);
      }
    }

    // 检查所有下载是否完成
    checkAllDownloadsComplete();
  } catch (error) {
    console.error("下载失败:", error);
    ElMessage.error(`下载失败: ${error}`);
    // 发生错误时也重置状态
    isDownloading.value = false;
    downloadingTasks.value.clear();
  }
};

const resetDownloadState = () => {
  isDownloading.value = false;
};

// 获取失败的下载项
const getFailedItems = () => {
  return Object.keys(downloadProgress.value).filter(id => 
    downloadProgress.value[id].status === 'error'
  );
};

// 选择所有失败的项
const selectFailedItems = () => {
  const failedIds = getFailedItems();
  selectedVideos.value = failedIds;
  
  // 更新全选状态
  const checkedCount = selectedVideos.value.length;
  const newAllSelected = checkedCount === contentList.value.length;
  allSelected.value = newAllSelected;
  isIndeterminate.value = checkedCount > 0 && checkedCount < contentList.value.length;
  
  if (failedIds.length > 0) {
    ElMessage.info(`已选择 ${failedIds.length} 个失败的下载项`);
  }
};

// 检查所有下载任务是否完成
const checkAllDownloadsComplete = () => {
  // 只有在下载状态时才检查
  if (!isDownloading.value) return;
  
  // 检查是否还有待下载的任务
  if (downloadingTasks.value.size === 0) {
    // 所有任务都完成了，重置下载状态
    isDownloading.value = false;
    
    // 显示下载完成的统计信息
    const downloadTasks = Object.values(downloadProgress.value);
    const completedCount = downloadTasks.filter(task => task.status === 'completed').length;
    const failedCount = downloadTasks.filter(task => task.status === 'error').length;
    const cancelledCount = downloadTasks.filter(task => task.status === 'cancelled').length;
    
    // 自动重新选择失败的内容
    if (failedCount > 0) {
      const failedContentIds = new Set<string>();
      
      // 收集所有失败的内容ID
      Object.keys(downloadProgress.value).forEach(key => {
        const task = downloadProgress.value[key];
        if (task.status === 'error') {
          // 处理图片下载的情况（ID格式为 contentId_imageIndex）
          const [contentId] = key.split('_');
          failedContentIds.add(contentId);
        }
      });
      
      // 重新选择失败的内容
      const failedIds = Array.from(failedContentIds).filter(id => 
        contentList.value.some(content => content.id === id)
      );
      
      if (failedIds.length > 0) {
        selectedVideos.value = failedIds;
        allSelected.value = false;
        isIndeterminate.value = failedIds.length > 0 && failedIds.length < contentList.value.length;
        
        ElMessage.warning(`已重新选择 ${failedIds.length} 个失败的内容，您可以重新下载`);
      } else {
        // 没有失败的内容，清空选择
        selectedVideos.value = [];
        allSelected.value = false;
        isIndeterminate.value = false;
      }
    } else {
      // 没有失败的内容，清空选择
      selectedVideos.value = [];
      allSelected.value = false;
      isIndeterminate.value = false;
    }
    
    if (completedCount > 0) {
      ElMessage.success(`下载完成: ${completedCount} 个成功${failedCount > 0 ? `, ${failedCount} 个失败` : ''}${cancelledCount > 0 ? `, ${cancelledCount} 个取消` : ''}`);
    } else if (failedCount > 0) {
      ElMessage.error(`下载失败: ${failedCount} 个失败${cancelledCount > 0 ? `, ${cancelledCount} 个取消` : ''}`);
    }
  }
};

defineExpose({
  resetDownloadState,
});

// 初始加载
onMounted(() => {
  if (props.creatorId) {
    fetchVideos();
  }
  
  // 监听下载进度更新
  window.electronAPI.onDownloadUpdate((data: any) => {
    console.log("window.electronAPI.onDownloadUpdate data:", data)
    // 更新单个图片的下载进度
    downloadProgress.value[data.id] = data;

    // 如果是图片下载，更新父内容的总进度
    const [contentId, imageIndex] = data.id.split('_');
    if (imageIndex !== undefined) {
      const content = contentList.value.find(c => c.id === contentId);
      if (content?.content_type === 'note' && content.image_urls) {
        const totalImages = content.image_urls.length;
        const completedImages = Object.keys(downloadProgress.value)
          .filter(key => key.startsWith(contentId + '_') && 
                 downloadProgress.value[key].status === 'completed')
          .length;
        
        const failedImages = Object.keys(downloadProgress.value)
          .filter(key => key.startsWith(contentId + '_') && 
                 downloadProgress.value[key].status === 'error')
          .length;

        // 更新父内容的总进度
        downloadProgress.value[contentId] = {
          progress: (completedImages / totalImages) * 100,
          status: completedImages === totalImages ? 'completed' : 
                  (failedImages > 0 && (completedImages + failedImages) === totalImages) ? 'error' : 'downloading',
          totalBytes: data.totalBytes,
          receivedBytes: data.receivedBytes,
        };
        
        // 如果图文内容所有图片都处理完了（完成或失败），从待下载任务中移除
        if ((completedImages + failedImages) === totalImages) {
          downloadingTasks.value.delete(contentId);
        }
      }
    } else {
      // 如果是视频下载，检查是否完成或失败
      if (data.status === 'completed' || data.status === 'error' || data.status === 'cancelled') {
        downloadingTasks.value.delete(data.id);
      }
    }
    
    // 检查所有下载是否完成
    checkAllDownloadsComplete();
  });
});

const downloadProgress = ref<Record<string, any>>({});

watch(() => props.contentList, (newVal) => {
  if (newVal) {
    contentList.value = [...newVal];
  }
}, { deep: true });
</script>

<style scoped>
.video-list-container {
  height: 660px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.video-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #f9fafb;
  border-bottom: 1px solid #e4e7ec;
}

.selection-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.selected-count {
  color: #6366f1;
  font-weight: 500;
  font-size: 14px;
}

.download-controls {
  display: flex;
  gap: 12px;
}

.download-controls .el-button {
  height: 36px;
  padding: 0 20px;
  font-size: 14px;
}

.waterfall-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
}

.waterfall-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  padding: 4px;
}

/* B站横版视频需要更大的网格 */
.platform-bili.waterfall-container {
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}

.video-item {
  aspect-ratio: 9/16; /* 默认竖版比例 */
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
  background: #f9fafb;
  border: 1px solid #e4e7ec;
}

/* B站横版视频比例 - 使用更高优先级 */
.waterfall-container.platform-bili .video-item {
  aspect-ratio: 16/9 !important;
}

.video-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
  border-color: #6366f1;
}

.video-item.selected {
  border-color: #6366f1;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12);
}

.video-select {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  padding: 4px;
  transition: opacity 0.3s ease;
}

.video-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
  backdrop-filter: blur(8px);
}

.video-info h3 {
  color: #fff;
  font-size: 13px;
  line-height: 1.4;
  margin: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.content-type-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff !important;
}



.content-type-badge .el-icon {
  font-size: 14px;
  color: #fff;
}

.content-type-badge.video {
  color: #6366f1;
}

.content-type-badge.note {
  color: #f59e0b;
}

.error-message {
  text-align: center;
  color: #f56c6c;
  margin: 16px 0;
  font-size: 14px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px 0;
}

/* 自定义滚动条样式 */
.waterfall-wrapper::-webkit-scrollbar {
  width: 6px;
}

.waterfall-wrapper::-webkit-scrollbar-thumb {
  background-color: #e0e0e0;
  border-radius: 3px;
}

.waterfall-wrapper::-webkit-scrollbar-track {
  background-color: #f5f5f5;
}

/* 修改图片加载函数以适应新的网格尺寸 */

.download-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(57, 62, 70, 0.95);
  backdrop-filter: blur(4px);
  padding: 12px;
  transition: all 0.3s ease;
}

.download-completed {
  background: rgba(99, 102, 241, 0.95);
}

.download-error {
  background: rgba(245, 108, 108, 0.95);
}

.download-cancelled {
  background: rgba(144, 147, 153, 0.95);
}

.download-pending {
  background: rgba(230, 162, 60, 0.95);
}

/* 自定义 Element Plus 按钮样式 */
:deep(.el-button--primary) {
  background-color: #6366f1 !important;
  border-color: #6366f1 !important;
  color: #ffffff !important;
}

:deep(.el-button--primary:hover) {
  background-color: #6366f1 !important;
  border-color: #6366f1 !important;
}

:deep(.el-button--primary:active) {
  background-color: hsl(239, 84%, 67%) !important;
  border-color: #6366f1 !important;
}

:deep(.el-button--primary.is-disabled) {
  background-color: rgba(99, 102, 241, 0.5) !important;
  border-color: rgba(99, 102, 241, 0.5) !important;
}

/* 自定义复选框样式 */
:deep(.el-checkbox) {
  margin-right: 0;
  height: auto;
}

:deep(.el-checkbox__inner) {
  width: 20px;
  height: 20px;
  border: 2px solid #fff;
  background-color: rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

:deep(.el-checkbox__inner::after) {
  height: 10px;
  left: 6px;
  width: 4px;
  border-width: 2px;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #6366f1;
  border-color: #6366f1;
}

:deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: #6366f1;
  border-color: #6366f1;
}

:deep(.el-checkbox__inner:hover) {
  border-color: #6366f1;
}

/* 加载更多按钮样式 */
.load-more {
  margin-top: 16px;
}

:deep(.load-more .el-button) {
  background-color: transparent;
  border-color: #6366f1;
  color: #6366f1;
}

:deep(.load-more .el-button:hover) {
  background-color: rgba(99, 102, 241, 0.1);
  border-color: #6366f1;
  color: #6366f1;
}

/* 选中数量文本颜色 */
.selected-count {
  color: #6366f1;
  font-weight: 500;
  min-width: 120px;
}

.skeleton-item {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: #f8f9fa;
  border: 1px solid #e4e7ec;
  aspect-ratio: 9/16; /* 默认竖版比例 */
}

/* B站横版视频骨架屏比例 - 使用更高优先级 */
.waterfall-container.platform-bili .skeleton-item {
  aspect-ratio: 16/9 !important;
}

.skeleton-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.skeleton-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.05));
}

.skeleton-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
}

.skeleton-checkbox {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.image-error {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fdf6ec;
  color: #e6a23c;
  font-size: 24px;
}

.image-error.bili-error {
  background: #f0f9ff;
  color: #6366f1;
}

.error-text {
  margin-top: 8px;
  font-size: 12px;
  font-weight: 500;
}

/* 图片加载过渡效果 */
.el-image {
  width: 100%;
  height: 100%;
  transition: opacity 0.3s ease;
}

.el-image.is-loading {
  opacity: 0;
}

.el-image.is-loaded {
  opacity: 1;
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 0;
  color: #909399;
  font-size: 14px;
}

.loading-icon {
  margin-right: 8px;
  animation: rotate 1s linear infinite;
}

.no-more {
  text-align: center;
  padding: 20px 0;
  color: #909399;
  font-size: 14px;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.content-type-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #fff;
  backdrop-filter: blur(4px);
  z-index: 2;
}

.content-type-badge.video {
  background-color: rgba(99, 102, 241, 0.8);
}

.content-type-badge.note {
  background-color: rgba(230, 162, 60, 0.8);
}

.content-type-badge .el-icon {
  font-size: 14px;
}

/* 更新列表和操作按钮样式 */
.content-list {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.operation-bar {
  margin-bottom: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #6366f1;
  border-color: #6366f1;
}

:deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: #6366f1;
  border-color: #6366f1;
}

:deep(.el-checkbox__inner:hover) {
  border-color: #6366f1;
}

.el-button--primary {
  background-color: #6366f1;
  border-color: #6366f1;
  border-radius: 8px;
}

.el-button--primary:hover {
  background-color: #4f46e5;
  border-color: #4f46e5;
}

.content-item {
  border: 1px solid #e4e7ec;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.content-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.item-info {
  padding: 16px;
  background: #fff;
}

.item-title {
  color: #111827;
  font-weight: 500;
}

.item-stats {
  color: #6366f1;
}

/* 更新视频项的标签和选择框样式 */
.video-select {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  padding: 4px;
  transition: opacity 0.3s ease;
}

/* 自定义复选框样式 */
:deep(.el-checkbox) {
  margin-right: 0;
  height: auto;
}

:deep(.el-checkbox__inner) {
  width: 20px;
  height: 20px;
  border: 2px solid #fff;
  background-color: rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

:deep(.el-checkbox__inner::after) {
  height: 10px;
  left: 6px;
  width: 4px;
  border-width: 2px;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #6366f1;
  border-color: #6366f1;
}

:deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: #6366f1;
  border-color: #6366f1;
}

:deep(.el-checkbox__inner:hover) {
  border-color: #6366f1;
}

/* 内容类型标签样式 */
.content-type-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.content-type-badge .el-icon {
  font-size: 14px;
}

.content-type-badge.video {
  color: #6366f1;
}

.content-type-badge.note {
  color: #f59e0b;
}

/* 视频项选中状态样式 */
.video-item.selected {
  border-color: #6366f1;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12);
}

.video-item.selected .video-select {
  opacity: 1;
}

.video-item.selected :deep(.el-checkbox__inner) {
  background-color: #6366f1;
  border-color: #6366f1;
}

/* 视频项悬停状态 */
.video-item:hover .video-select {
  opacity: 1;
}

.video-item:hover :deep(.el-checkbox__inner) {
  border-color: #6366f1;
}

.video-cover {
  position: relative;
  width: 100%;
  height: 100%;
}

.el-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style> 