# 视频音频提取与语音识别脚本

## 功能说明

此脚本用于处理今天爬取的所有平台视频数据：

1. **读取数据**: 自动扫描 `data/` 目录下今天的 CSV 文件
2. **下载视频**: 从抖音、小红书、B站、快手等平台下载视频
3. **提取音频**: 使用 PyAV 从视频中提取音频
4. **语音识别**: 使用 faster-whisper (本地 Whisper 模型) 进行语音转文字
5. **保存结果**: 将转写文本保存到 `data/transcripts/` 目录

## 安装依赖

```bash
# 方法1: 使用根目录的虚拟环境 (推荐)
cd C:\code\todolist_free_todo_dev\LifeTrace
uv sync

# 方法2: 单独安装脚本依赖
cd MediaCrawlerPro-Python\scripts
pip install -r requirements_transcribe.txt
```

## 使用方法

```bash
# 确保在 LifeTrace 项目根目录激活虚拟环境
cd C:\code\todolist_free_todo_dev\LifeTrace

# 运行脚本
python MediaCrawlerPro-Python\scripts\extract_video_audio_text.py
```

## 输出目录

转写结果保存在:
```
MediaCrawlerPro-Python/data/transcripts/
├── douyin/
│   └── {video_id}_{title}_{date}.txt
├── xhs/
│   └── {note_id}_{title}_{date}.txt
├── bilibili/
│   └── {video_id}_{title}_{date}.txt
└── kuaishou/
    └── {video_id}_{title}_{date}.txt
```

## 输出文件格式

每个转写文件包含：

```
标题: [视频标题]
平台: [平台名称]
内容ID: [内容ID]
视频URL: [原始视频URL]
转写时间: [处理时间]

========== 转写文本 ==========

[语音识别出的文本内容]
```

## 配置选项

在脚本中可以修改以下参数：

```python
# Whisper 模型大小 (越大越准确但越慢)
# 可选: tiny, base, small, medium, large-v2, large-v3
model_size = "base"

# 设备类型
# auto: 自动选择
# cpu: 强制使用CPU
# cuda: 使用GPU (需要CUDA)
device = "auto"
```

## 支持的平台

| 平台 | 视频URL字段 | 内容ID字段 |
|------|-------------|------------|
| 抖音 | video_download_url | aweme_id |
| 小红书 | video_url | note_id |
| B站 | video_url | video_id |
| 快手 | video_url | video_id |

## 注意事项

1. 首次运行时会自动下载 Whisper 模型（约 140MB for base）
2. 视频下载需要良好的网络连接
3. 处理时间取决于视频数量和长度
4. 建议在有 GPU 的机器上运行以提高速度
