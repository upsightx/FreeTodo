<template>
  <el-watermark
    content="仅供个人学习使用，严禁用于商业用途。"
    :gap="[300, 300]"
  >
    <el-container class="media-crawler-downloader">
      <el-header height="60px">
        <el-button
          icon="el-icon-github"
          link
          @click="
            openExternal('https://github.com/MediaCrawlerPro/MediaCrawlerPro-Downloader')
          "
        >
          <span
            style="
              font-size: 28px;
              font-weight: bold;
              cursor: pointer;
              color: #eeeeee;
            "
            >MediaCrawlerProDownloader自媒体平台下载器</span
          >
        </el-button>
      </el-header>
      <el-container class="main-content">
        <el-aside width="450px" style="overflow: hidden;">
          <el-card class="input-card">
            <el-form label-position="top" class="download-form">
              <el-form-item>
                <div class="mode-switch-container">
                  <div 
                    class="mode-switch-option" 
                    :class="{ active: mode === 'creator' }"
                    @click="mode = 'creator'"
                  >
                    下载用户主页
                  </div>
                  <div 
                    class="mode-switch-option" 
                    :class="{ active: mode === 'video' }"
                    @click="mode = 'video'"
                  >
                    视频详情下载
                  </div>
                  <div 
                    class="mode-switch-slider" 
                    :class="{ video: mode === 'video' }"
                  ></div>
                </div>

                <div class="platform-options">
                  <div 
                    class="platform-option" 
                    :class="{ selected: platform === 'dy' }"
                    @click="platform = 'dy'"
                  >
                    <div class="platform-icon">
                      <img src="../assets/douyin_icon.png" alt="抖音" />
                    </div>
                    <div class="platform-info">
                      <div class="platform-name">抖音</div>
                    </div>
                  </div>
                  
                  <div 
                    class="platform-option" 
                    :class="{ selected: platform === 'xhs' }"
                    @click="platform = 'xhs'"
                  >
                    <div class="platform-icon">
                      <img src="../assets/xiaohongshu_icon.png" alt="小红书" />
                    </div>
                    <div class="platform-info">
                      <div class="platform-name">小红书</div>
                    </div>
                  </div>

                  <div 
                    class="platform-option" 
                    :class="{ selected: platform === 'ks' }"
                    @click="platform = 'ks'"
                  >
                    <div class="platform-icon">
                      <img src="../assets/kuaishou_icon.png" alt="快手" />
                    </div>
                    <div class="platform-info">
                      <div class="platform-name">快手</div>
                    </div>
                  </div>

                  <div 
                    class="platform-option" 
                    :class="{ selected: platform === 'bili' }"
                    @click="platform = 'bili'"
                  >
                    <div class="platform-icon">
                      <img src="../assets/bilibili_icon.png" alt="B站" />
                    </div>
                    <div class="platform-info">
                      <div class="platform-name">B站</div>
                    </div>
                  </div>
                </div>

                <div class="input-section">
                  <div class="section-title">
                    <el-icon><Link /></el-icon>
                    输入地址
                  </div>
                  <el-input
                    v-model="url"
                    size="large"
                    placeholder="请输入主页地址或视频详情页地址"
                    ref="urlInputRef"
                  >
                    <template #prefix>
                      <el-icon><Link /></el-icon>
                    </template>
                  </el-input>
                </div>

                <div class="input-section">
                  <div class="section-title">
                    <el-icon><Document /></el-icon>
                    登录成功后的cookies
                  </div>
                  <el-input
                    v-model="cookies"
                    type="textarea"
                    :rows="5"
                    placeholder="请输入cookies信息"
                    resize="none"
                  />
                </div>

                <div class="query-button">
                  <el-button
                    type="primary"
                    :disabled="isQuerying"
                    @click="startQueryInfo"
                    :loading="isQuerying"
                  >
                    {{ isQuerying ? "正在查询..." : "开始查询" }}
                  </el-button>
                </div>

              </el-form-item>              
            </el-form>
          </el-card>
        </el-aside>
        <el-main>
          <template v-if="isQuerying">
            <div class="query-loading">
              <el-skeleton :loading="true" animated>
                <template #template>
                  <div class="creator-skeleton" :class="`platform-${platform}`">
                    <el-skeleton-item
                      v-if="mode === 'creator'"
                      variant="h1"
                      style="width: 100%; height: 60px; margin-bottom: 20px"
                    />
                    <div class="video-grid-skeleton">
                      <div
                        v-for="i in mode === 'creator' ? 12 : 1"
                        :key="i"
                        class="video-skeleton-item"
                      >
                        <el-skeleton-item
                          variant="image"
                          style="width: 100%; height: 100%"
                        />
                        <el-skeleton-item
                          variant="p"
                          style="width: 60%; margin-top: 8px"
                        />
                      </div>
                    </div>
                  </div>
                </template>
              </el-skeleton>
            </div>
          </template>
          <template v-else-if="mode === 'creator' && creatorInfo.user_id">
            <CreatorInfoComponent :creatorInfo="creatorInfo" />
            <ContentListComponent
              ref="videoListRef"
              :creator-id="creatorInfo.user_id"
              :cookies="cookies"
              :platform="platform"
              :content-list="contentList"
              @select-videos="handleVideoSelect"
              @download-videos="handleDownloadVideos"
            />
          </template>
          <template v-else-if="mode === 'video' && !isQuerying && contentList.length > 0">
            <ContentListComponent
              ref="videoListRef"
              :content-list="contentList"
              :cookies="cookies"
              :platform="platform"
              @select-videos="handleVideoSelect"
              @download-videos="handleDownloadVideos"
            />
          </template>
          <template v-else>
            <div class="empty-state">
              <div class="empty-state-content">
                <el-icon class="empty-icon"><Search /></el-icon>
                <h3 class="empty-title">开始您的内容载之旅</h3>
                <div class="empty-steps">
                  <div class="step-item">
                    <div class="step-number">1</div>
                    <div class="step-text">
                      <h4>选择平台</h4>
                      <p>选择对应自媒体平台</p>
                    </div>
                  </div>
                  <div class="step-item">
                    <div class="step-number">2</div>
                    <div class="step-text">
                      <h4>输入地址</h4>
                      <p>粘贴用户主页或视频链接</p>
                    </div>
                  </div>
                  <div class="step-item">
                    <div class="step-number">3</div>
                    <div class="step-text">
                      <h4>填写Cookie</h4>
                      <p>登录后获取Cookie信息</p>
                    </div>
                  </div>
                </div>
                <div class="empty-action">
                  <el-button type="primary" @click="focusUrlInput">
                    <el-icon><Link /></el-icon>
                    立即开始
                  </el-button>
                </div>
              </div>
            </div>
          </template>
        </el-main>
      </el-container>
      <Footer />
    
    </el-container>
  </el-watermark>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import axios from "axios";
import { ElMessage } from "element-plus";
import type { CreatorInfoResponse } from "../typings/creator";
import type { CreatorInfo } from "../typings/creator";
import ContentListComponent from "./ContentList.vue";
import CreatorInfoComponent from "./CreatorInfo.vue";
import Footer from "./Footer.vue";
import { apiService } from "../api";
import { Content } from "../typings/content";
import { Link, Document, Search } from '@element-plus/icons-vue'
import { openExternal } from "../utils/utils";

const platform = ref<string>("dy");
const mode = ref<string>("creator");
const url = ref<string>("");
const totalVideos = ref<number>(0);
const cookies = ref<string>("");
const isQuerying = ref<boolean>(false);
const creatorInfo = ref<CreatorInfo>({
  nickname: "",
  avatar: "",
  description: "",
  user_id: "",
  follower_count: "",
  following_count: "",
  content_count: "",
});
const selectedVideos = ref<string[]>([]);
const contentList = ref<Content[]>([]);
const urlInputRef = ref<HTMLInputElement | null>(null);

const queryCreatorInfo = async (): Promise<CreatorInfoResponse> => {
  try {
    const response = await apiService.queryCreatorInfo({
      platform: platform.value,
      creator_url: url.value,
      cookies: cookies.value,
    });

    if (!response.isok) {
      throw new Error(response.msg);
    }

    return response;
  } catch (error) {
    console.error("查询创作者信息失败:", error);
    handleApiError(error);
    throw error;
  }
};

const startQueryInfo = async () => {
  if (!url.value || !cookies.value) {
    ElMessage.error("请输入完整信息");
    return;
  }


  try {
    isQuerying.value = true;
    totalVideos.value = 0;
    contentList.value = [];
    creatorInfo.value = {
      nickname: "",
      avatar: "",
      description: "",
      user_id: "",
      follower_count: "",
      following_count: "",
      content_count: "",
    };

    if (mode.value === "creator") {
      const response = await queryCreatorInfo();
      if (!response.isok) {
        console.log(response);
        ElMessage.error(response.msg);
        return;
      }
      creatorInfo.value = response.data;
    } else if (mode.value === "video") {
      // 查询单个内容详情
      const response = await apiService.queryContentDetail({
        platform: platform.value,
        content_url: url.value,
        cookies: cookies.value,
      });

      if (!response.isok) {
        ElMessage.error(response.msg);
        return;
      }

      // 将单个内容添加到内容列表中
      contentList.value = [response.data.content];
    }
  } catch (error) {
    console.error("查询失败:", error);
    handleApiError(error);
  } finally {
    isQuerying.value = false;
  }
};

const handleApiError = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    if (error.code === "ECONNREFUSED") {
      ElMessage.error("无法连接到服务器，请确保服务器已启动");
    } else if (error.response) {
      ElMessage.error(`操作失败: ${error.response.data.msg || "未知错误"}`);
    } else {
      ElMessage.error("网络连接失败，请检查网络设置");
    }
  } else {
    ElMessage.error("作失败，请稍后重试");
  }
};

const handleDownloadVideos = async (data: {
  ContentList: Content[];
  saveDir: string;
}) => {
  try {
    const { ContentList, saveDir } = data;
    // 清除之前的下载任务
    if (window.electronAPI) {
      await window.electronAPI.clearDownloads();
    }

    // 批量开始下载所有选中的视频
    for (const video of ContentList) {
      // 处理文件名
      const sanitizedTitle = video.title
        .replace(/[\\/:*?"<>|]/g, "_") // 替换非法字符
        .replace(/\s+/g, "_") // 替换空格
        .replace(/_+/g, "_") // 合并多个下划线
        .replace(/#/g, "") // 替换#
        .slice(0, 50); // 限制长度为50个字符

      // 根据平台和内容类型确定文件扩展名
      let extension = '.mp4';
      if (video.content_type === 'note' && platform.value === 'xhs') {
        // 小红书的图片内容
        extension = video.image_urls && video.image_urls.length > 0 ? '.jpg' : '.mp4';
      } else if (platform.value === 'ks') {
        // 快手主要是视频内容
        extension = '.mp4';
      }
      const filename = `${sanitizedTitle}_${video.id}${extension}`;
      try {
        let actualVideo = video;
        
        // B站和XHS特殊处理 - 如果没有下载链接，需要先获取内容详情
        // 快手平台不需要额外获取详情，因为列表接口已经返回了完整的下载信息
        if ((platform.value === 'bili' || platform.value === 'xhs') && !video.video_download_url) {
          try {
            const response = await apiService.queryContentDetail({
              platform: platform.value,
              content_url: video.url,
              cookies: cookies.value,
            });

            if (!response.isok) {
              ElMessage.error(`获取${platform.value === 'bili' ? 'B站' : '小红书'}视频: ${video.title} 详情失败，跳过下载`);
              continue;
            }
            
            // 更新视频信息
            actualVideo = {
              ...video,
              video_download_url: response.data.content.video_download_url,
              extria_info: response.data.content.extria_info
            };
          } catch (error) {
            console.error(`获取${platform.value === 'bili' ? 'B站' : '小红书'}视频详情失败:`, error);
            ElMessage.error(`获取${platform.value === 'bili' ? 'B站' : '小红书'}视频: ${video.title} 详情失败，跳过下载`);
            continue;
          }
        }

        let downloadParams = [
          platform.value,
          actualVideo.id,
          actualVideo.video_download_url,
          filename,
          saveDir,
          actualVideo.id // 使用video.id作为contentId
        ];

        // B站DASH格式需要传递Cookie和音频URL
        if (platform.value === 'bili') {
          const extraInfo = actualVideo.extria_info || {};
          downloadParams.push(cookies.value); // cookies
          downloadParams.push(extraInfo.audio_url || ''); // audioUrl
        }
        // 快手平台只需要基础参数，不需要额外的Cookie或音频URL
        // 其他平台也使用基础参数

        const result = await window.electronAPI.startDownload(...downloadParams);

        if (!result) {
          ElMessage.error(`开始下载视频 ${video.title} 失败`);
        }

        // 下载封面图片（如果有封面URL）
        if (video.cover_url) {
          const coverExtension = video.cover_url.includes('.jpg') ? '.jpg' : 
                                video.cover_url.includes('.png') ? '.png' : 
                                video.cover_url.includes('.webp') ? '.webp' : '.jpg';
          const coverFilename = `${sanitizedTitle}_${video.id}_cover${coverExtension}`;
          
          let coverDownloadParams = [
            platform.value,
            `${video.id}_cover`,
            video.cover_url,
            coverFilename,
            saveDir,
            video.id // 使用video.id作为contentId
          ];

          // B站封面下载也需要Cookie
          if (platform.value === 'bili') {
            coverDownloadParams.push(cookies.value); // cookies
            coverDownloadParams.push(''); // audioUrl (封面不需要音频)
          }
          // 快手封面下载不需要额外参数

          await window.electronAPI.startDownload(...coverDownloadParams);
        }
      } catch (error) {
        console.error(`下载视频 ${video.title} 失败:`, error);
        ElMessage.error(`下载视频 ${video.title} 失败`);
      }
    }
  } catch (error) {
    console.error("批量下载失败:", error);
    handleApiError(error);
  }
};

const handleVideoSelect = (videos: string[]) => {
  selectedVideos.value = videos;
};

onMounted(() => {
  if (window.electronAPI) {    
    window.electronAPI.onDownloadMessage(
      (data: { type: string; message: string }) => {
        if (data.type === "error") {
          ElMessage.error(data.message);
        } else if (data.type === "success") {
          ElMessage.success(data.message);
        }
      }
    );
  }
});

const focusUrlInput = () => {
  if (urlInputRef.value) {
    urlInputRef.value.focus();
  }
}
</script>

<style scoped>
.media-crawler-downloader {
  display: flex;
  flex-direction: column;
  background-color: #eeeeee;
  color: #333;
}

.el-header {
  background-color: #6366f1;
  color: #eeeeee;
  text-align: center;
  line-height: 60px;
  padding: 0 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.main-content {
  flex-grow: 1;
  display: flex;
  padding: 20px 0px;
  gap: 20px;
  margin-top: 10px;
}

.el-aside,
.el-main {
  padding: 0 !important;
}

.input-card,
.progress-card {
  padding-top: 10px;
  height: 800px;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.download-form {
  padding: 24px;
  height: 100%;
  overflow-y: hidden;
  background-color: #fafafa;
  border-radius: 12px;
}

.progress-card {
  display: flex;
  flex-direction: column;
}

.progress-summary {
  padding: 10px;
  font-weight: bold;
  color: #6366f1;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.1);
  margin: 10px;
  text-align: center;
}

.progress-list {
  flex-grow: 1;
  overflow-y: hidden; /* 隐藏动条 */
  padding: 0 20px 20px;
}

.video-progress {
  margin-bottom: 15px;
}

.directory-input {
  display: flex;
  gap: 10px;
  width: 100%;
}

.directory-input .el-input {
  flex-grow: 1;
}

.el-button {
  width: 100%;
  height: 44px;
  background-color: #6366f1;
  border-color: #6366f1;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
}

.el-button:hover {
  background-color: #4f46e5;
  border-color: #4f46e5;
}

/* 覆盖 Element Plus 默认样式 */
:deep(.el-card__body) {
  height: 100%;
  padding: 0;
  display: flex;
  flex-direction: column;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

/* 覆盖 Element Plus 选择器和进度条的默认样式 */
:deep(.el-select .el-input__inner) {
  border-color: #6366f1;
}

:deep(.el-select .el-input__inner:focus, .el-select .el-input__inner:hover) {
  border-color: #6366f1;
}

:deep(.el-option--selected) {
  background-color: #6366f1 !important;
  color: #ffffff;
}

:deep(.el-progress-bar__inner) {
  background-color: #6366f1;
}
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #6366f1 !important;
}
:deep(.el-textarea__inner.is-focus) {
  box-shadow: 0 0 0 1px #6366f1 !important;
}
:deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px #6366f1 !important;
}
:deep(.el-select-dropdown__item:hover) {
  background-color: #6366f1 !important;
  color: #ffffff !important;
}

:deep(.el-select-dropdown__item.selected) {
  background-color: #6366f1 !important;
  color: #ffffff !important;
}

/* 调整主内容区域的样式 */
.el-main {
  padding: 20px;
  background-color: #f5f7fa;
}


.el-link {
  font-weight: normal;
  &:hover {
    color: #6366f1;
  }
}

.external-icon {
  margin-left: 4px;
  font-size: 12px;
  opacity: 0.8;
}

.empty-container {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

:deep(.el-link) {
  color: #6366f1 !important;
  transition: color 0.3s ease;
}

:deep(.el-link:hover) {
  color: #00fff5 !important;
}

:deep(.el-link:hover .el-icon) {
  opacity: 1;
  transform: translateX(2px);
  transition: all 0.3s ease;
}

.query-loading {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.creator-skeleton {
  width: 100%;
}

.video-grid-skeleton {
  display: grid;
  gap: 12px;
  padding: 12px;
}

/* 默认网格（其他平台3:4比例）*/
.video-grid-skeleton {
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
}

/* B站横版视频网格（16:9比例）*/
.platform-bili .video-grid-skeleton {
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}

.video-skeleton-item {
  position: relative;
  border-radius: 6px;
  overflow: hidden;
  background: #f8f9fa;
  aspect-ratio: 3/4; /* 默认3:4比例 */
}

/* B站骨架屏项目16:9比例 */
.platform-bili .video-skeleton-item {
  aspect-ratio: 16/9;
}

.social-icons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
  /* margin-top: 20px; */
  /* padding: 16px; */
  border-top: 1px solid #f0f0f0;
}

.icon-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 26px;
}

.icon-item .el-button {
  padding: 8px;
  transition: all 0.3s ease;
}

.icon-item .el-button:hover {
  transform: translateY(-2px);
}

.social-icon {
  width: 36px;
  height: 36px;
  object-fit: contain;
  transition: all 0.3s ease;
}

.qr-code-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
}

.qr-code {
  width: 160px;
  height: 160px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 8px;
}

.qr-code-container p {
  margin: 0;
  font-size: 14px;
  color: #666;
}

:deep(.wechat-qr-popover) {
  padding: 0;
  border-radius: 8px;
}

/* 表单项样式 */
:deep(.el-form-item__label) {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  padding-bottom: 8px;
}

/* Select 选择器样式 */
:deep(.el-select) {
  width: 100%;
}

:deep(.el-select .el-input__wrapper) {
  background-color: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  box-shadow: none !important;
  border: 1px solid #e4e7ec;
}

:deep(.el-select .el-input__wrapper:hover) {
  border-color: #c0c4cc;
}

:deep(.el-select .el-input__wrapper.is-focus) {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1) !important;
}

/* 输入框样式 */
:deep(.el-input__wrapper) {
  background-color: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  box-shadow: none !important;
  border: 1px solid #e4e7ec;
}

:deep(.el-input__wrapper:hover) {
  border-color: #c0c4cc;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1) !important;
}

/* 文本域样式 */
:deep(.el-textarea__inner) {
  background-color: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  border: 1px solid #e4e7ec;
}

:deep(.el-textarea__inner:hover) {
  border-color: #c0c4cc;
}

:deep(.el-textarea__inner:focus) {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1) !important;
}

/* 下拉选项样式 */
:deep(.el-select-dropdown__item) {
  padding: 10px 16px;
  font-size: 14px;
}

:deep(.el-select-dropdown__item.selected) {
  background-color: #6366f1 !important;
  color: #ffffff !important;
  font-weight: 500;
}

:deep(.el-select-dropdown__item:hover) {
  background-color: #f3f4f6 !important;
  color: #6366f1 !important;
}

.mode-switch-container {
  background: #f4f4f5;
  border-radius: 12px;
  padding: 4px;
  display: flex;
  position: relative;
  margin-bottom: 24px;
  margin-top: 20px;
}

.mode-switch-option {
  flex: 1;
  padding: 8px 16px;
  text-align: center;
  cursor: pointer;
  position: relative;
  z-index: 1;
  transition: color 0.3s ease;
  font-weight: 500;
  color: #666;
}

.mode-switch-option.active {
  color: #111827;
}

.mode-switch-slider {
  position: absolute;
  top: 4px;
  left: 4px;
  height: calc(100% - 8px);
  width: calc(50% - 4px);
  background: white;
  border-radius: 8px;
  transition: transform 0.3s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.mode-switch-slider.video {
  transform: translateX(100%);
}

.platform-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;

  width: 100%;
  box-sizing: border-box;
}

.platform-option {
  background: white;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 48px;
}

.platform-option:hover {
  border-color: #6366f1;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
}

.platform-option.selected {
  border-color: #6366f1;
  background: #f5f7ff;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12);
}

.platform-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: #f9fafb;
  padding: 6px;
}

.platform-icon img {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.platform-info {
  flex: 1;
  min-width: 0;
}

.platform-name {
  font-weight: 500;
  color: #111827;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.input-section {
  margin-top: 24px;
  background: white;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #e4e7ec;
  transition: all 0.3s ease;
  width: 100%;
  box-sizing: border-box;
}

.input-section:hover {
  border-color: #6366f1;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.08);
}

.input-section:focus-within {
  border-color: #6366f1;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title .el-icon {
  font-size: 16px;
  color: #6366f1;
}

/* 输入框样式优化 */
:deep(.el-input) {
  width: 100%;
  box-sizing: border-box;
}

:deep(.el-input__wrapper) {
  width: 100%;
  box-shadow: none !important;
  background: #f9fafb;
  border-radius: 8px;
  padding: 8px 12px;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

:deep(.el-textarea) {
  width: 100%;
  box-sizing: border-box;
}

:deep(.el-textarea__inner) {
  width: 100%;
  box-shadow: none !important;
  background: #f9fafb;
  border-radius: 8px;
  padding: 12px;
  transition: all 0.3s ease;
  resize: none;
  box-sizing: border-box;
}

/* 调整表单容器宽度 */
.download-form {
  width: 100%;
  padding: 20px;
  box-sizing: border-box;
}

/* 调整卡片容器宽度 */
.input-card {
  width: 100%;
  padding: 0;
}

/* 调整aside宽度 */
.el-aside {
  width: 440px !important;
  padding: 0 20px;
  box-sizing: border-box;
}

/* 查询按钮样式优化 */
.query-button {
  margin-top: 24px;
  width: 100%;
}

:deep(.el-button--primary) {
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  background: #6366f1;
  border: none;
  box-shadow: 0 2px 4px rgba(99, 102, 241, 0.2);
  transition: all 0.3s ease;
}

:deep(.el-button--primary:hover) {
  background: #4f46e5;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(99, 102, 241, 0.25);
}

:deep(.el-button--primary:active) {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(99, 102, 241, 0.2);
}

/* 调整el-form-item的样式 */
:deep(.el-form-item) {
  margin-bottom: 0;
  width: 100%;
}

:deep(.el-form-item__content) {
  width: 100%;
}

/* 确保输入框和文本域不会超出容器 */
:deep(.el-input), 
:deep(.el-textarea) {
  width: 100%;
  box-sizing: border-box;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  width: 100%;
  box-sizing: border-box;
}

/* 平台选择区域也需要调整 */
.platform-options {
  width: 100%;
  box-sizing: border-box;
}

.empty-state {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;  
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.empty-state-content {
  max-width: 600px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  color: #6366f1;
  margin-bottom: 24px;
}

.empty-title {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 32px;
}

.empty-steps {
  display: flex;
  gap: 32px;
  justify-content: center;
  margin-bottom: 40px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  text-align: left;
}

.step-number {
  width: 28px;
  height: 28px;
  background: #6366f1;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.step-text {
  flex: 1;
}

.step-text h4 {
  font-size: 16px;
  font-weight: 500;
  color: #111827;
  margin: 0 0 4px 0;
}

.step-text p {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.empty-action {
  margin-top: 32px;
}

.empty-action .el-button {
  padding: 12px 24px;
  font-size: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.empty-action .el-icon {
  font-size: 18px;
}
</style>