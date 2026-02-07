<template>

    <div class="social-icons">
        <div class="icon-item">
            <el-tooltip content="GitHub" placement="bottom">
                <el-button link @click="
                    openExternal(
                        'https://github.com/MediaCrawlerPro/MediaCrawlerPro-Downloader'
                    )
                    ">
                    <img src="../assets/github_icon.png" alt="GitHub" class="social-icon" />
                </el-button>
            </el-tooltip>
        </div>

        <div class="icon-item">
            <el-popover placement="right" :width="200" trigger="hover" popper-class="wechat-qr-popover">
                <template #reference>
                    <el-button link>
                        <img src="../assets/wechat_icon.png" alt="WeChat" class="social-icon" />
                    </el-button>
                </template>
                <div class="qr-code-container">
                    <img src="../assets/relakkes_weichat.jpg" alt="微信二维码" class="qr-code" />
                    <p>扫码添加作者微信</p>
                </div>
            </el-popover>
        </div>

        <div class="icon-item">
            <el-tooltip content="作者的B站" placement="bottom">
                <el-button link @click="
                    openExternal('https://space.bilibili.com/434377496')
                    ">
                    <img src="../assets/bilibili_icon.png" alt="Bilibili" class="social-icon" />
                </el-button>
            </el-tooltip>
        </div>

        <div class="icon-item">
            <el-tooltip content="作者的抖音" placement="bottom">
                <el-button link @click="
                    openExternal(
                        'https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE?from_tab_name=main&vid=7347350330633489705'
                    )
                    ">
                    <img src="../assets/douyin_icon.png" alt="GitHub" class="social-icon" />
                </el-button>
            </el-tooltip>
        </div>

        <div class="icon-item">
            <el-tooltip content="作者的小红书" placement="bottom">
                <el-button link @click="
                    openExternal(
                        'https://www.xiaohongshu.com/user/profile/5f58bd990000000001003753'
                    )
                    ">
                    <img src="../assets/xiaohongshu_icon.png" alt="GitHub" class="social-icon" />
                </el-button>
            </el-tooltip>
        </div>
    </div>
</template>

<script setup lang="ts">
import { openExternal } from "../utils/utils";
</script>


<style scoped>


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

</style>