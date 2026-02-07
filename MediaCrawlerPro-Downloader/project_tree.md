### MediaCrawlerPro-Downloader 项目目录结构
```tree
.                                                 # 项目根目录
├── DownloadServer                                # 下载服务端
│   ├── abs                                       # 抽象接口目录
│   │   └── abs_api_client.py                     # API客户端抽象类
│   ├── apis                                      # API接口目录
│   │   ├── base_handler.py                       # 基础处理器
│   │   ├── content_detail_handler.py             # 内容详情处理器
│   │   └── creator_query_handler.py              # 创作者查询处理器
│   ├── config                                    # 配置目录
│   │   └── base_config.py                        # 基础配置实现
│   ├── constant                                  # 常量目录
│   │   ├── base_constant.py                      # 基础常量定义
│   │   ├── bilibili.py                           # B站相关常量
│   │   ├── douyin.py                             # 抖音相关常量
│   │   ├── error_code.py                         # 错误码定义
│   │   ├── kuaishou.py                           # 快手相关常量
│   │   └── xiaohongshu.py                        # 小红书相关常量
│   ├── docs                                      # 文档目录
│   │   └── api                                   # API文档
│   │       └── swagger.yaml                      # Swagger接口文档
│   ├── logic                                     # 业务逻辑目录
│   │   ├── base_logic.py                         # 基础逻辑实现
│   │   ├── content_detail_logic.py               # 内容详情逻辑
│   │   └── creatory_query_logic.py               # 创作者查询逻辑
│   ├── logs                                      # 日志目录
│   │   ├── 2025-01-05.log                        # 日志文件
│   │   └── 2025-01-06.log                        # 日志文件
│   ├── models                                    # 数据模型目录
│   │   ├── base_model.py                         # 基础模型定义
│   │   ├── content_detail.py                     # 内容详情模型
│   │   └── creator.py                            # 创作者模型
│   ├── pkg                                       # 公共包目录
│   │   ├── cache                                 # 缓存模块
│   │   │   ├── abs_cache.py                      # 缓存抽象类
│   │   │   ├── cache_factory.py                  # 缓存工厂类
│   │   │   ├── local_cache.py                    # 本地缓存实现
│   │   │   └── redis_cache.py                    # Redis缓存实现
│   │   ├── custom_exceptions                     # 自定义异常目录
│   │   │   └── base_exceptions.py                # 基础异常定义
│   │   ├── media_platform_api                    # 媒体平台API目录
│   │   │   ├── bilibili                          # B站API实现
│   │   │   │   ├── client.py                     # B站客户端
│   │   │   │   ├── exception.py                  # B站异常定义
│   │   │   │   ├── extractor.py                  # B站数据提取器
│   │   │   │   └── field.py                      # B站字段定义
│   │   │   ├── douyin                            # 抖音API实现
│   │   │   │   ├── client.py                     # 抖音客户端
│   │   │   │   ├── extractor.py                  # 抖音数据提取器
│   │   │   │   └── help.py                       # 抖音帮助函数
│   │   │   ├── xhs                               # 小红书API实现
│   │   │   │   ├── client.py                     # 小红书客户端
│   │   │   │   ├── exception.py                  # 小红书异常定义
│   │   │   │   ├── extractor.py                  # 小红书数据提取器
│   │   │   │   ├── field.py                      # 小红书字段定义
│   │   │   │   └── help.py                       # 小红书帮助函数
│   │   │   └── media_platform_api.py             # 媒体平台API基类
│   │   ├── rpc                                   # RPC目录
│   │   │   └── sign_srv_client                   # 签名服务客户端
│   │   │       ├── sign_client.py                # 签名客户端实现
│   │   │       └── sign_model.py                 # 签名模型定义
│   │   ├── tools                                 # 工具目录
│   │   │   ├── crawler_util.py                   # 爬虫工具类
│   │   │   ├── time_util.py                      # 时间工具类
│   │   │   └── utils.py                          # 通用工具类
│   │   └── async_http_client.py                  # 异步HTTP客户端
│   ├── repo                                      # 数据仓库目录
│   ├── LICENSE                                   # 许可证文件
│   ├── README.md                                 # 说明文档
│   ├── app.py                                    # 应用入口
│   ├── context_vars.py                           # 上下文变量
│   ├── image.png                                 # 图片资源
│   ├── requirements.txt                          # 依赖清单
│   └── router.py                                 # 路由配置
├── DownloadUI                                    # 下载器UI项目
│   ├── build                                     # 构建目录
│   ├── scripts                                   # 脚本目录
│   │   ├── private                               # 私有脚本
│   │   │   └── tsc.js                            # TypeScript编译脚本
│   │   ├── build.js                              # 构建脚本
│   │   └── dev-server.js                         # 开发服务器脚本
│   ├── src                                       # 源码目录
│   │   ├── main                                  # 主进程目录（electron）
│   │   │   ├── static                            # 静态资源
│   │   │   ├── download-manager.ts               # 下载管理器
│   │   │   ├── main.ts                           # 主进程入口
│   │   │   ├── preload.ts                        # 预加载脚本
│   │   │   └── tsconfig.json                     # TS配置文件
│   │   └── renderer                              # 渲染进程目录（vue3 + element-plus）
│   │       ├── api                               # API目录
│   │       │   └── index.ts                      # API入口文件
│   │       ├── assets                            # 资源目录
│   │       │   ├── bilibili_icon.png             # B站图标
│   │       │   ├── douyin_icon.png               # 抖音图标
│   │       │   ├── github_icon.png               # GitHub图标
│   │       │   ├── kuaishou_icon.png             # 快手图标
│   │       │   ├── relakkes_weichat.jpg          # 微信二维码
│   │       │   ├── wechat_icon.png               # 微信图标
│   │       │   └── xiaohongshu_icon.png          # 小红书图标
│   │       ├── components                        # 组件目录
│   │       │   ├── ContactMe.vue                 # 联系我组件
│   │       │   ├── ContentList.vue               # 内容列表组件
│   │       │   ├── CreatorInfo.vue               # 创作者信息组件
│   │       │   ├── DownloadItem.vue              # 下载项组件
│   │       │   ├── Footer.vue                    # 页脚组件
│   │       │   └── Layout.vue                    # 布局组件
│   │       ├── public                            # 公共资源目录
│   │       │   ├── vite.svg                      # Vite图标
│   │       │   └── vue.svg                       # Vue图标
│   │       ├── typings                           # 类型定义目录
│   │       │   ├── content.d.ts                  # 内容类型定义
│   │       │   ├── creator.d.ts                  # 创作者类型定义
│   │       │   ├── download.d.ts                 # 下载类型定义
│   │       │   ├── electron-api.d.ts             # Electron API类型
│   │       │   ├── electron.d.ts                 # Electron类型
│   │       │   └── shims-vue.d.ts                # Vue类型定义
│   │       ├── utils                             # 工具目录
│   │       │   └── utils.ts                      # 工具函数
│   │       ├── App.vue                           # 根组件
│   │       ├── index.html                        # 入口HTML
│   │       ├── main.ts                           # 渲染进程入口
│   │       ├── style.css                         # 全局样式
│   │       └── tsconfig.json                     # TS配置文件
│   ├── LICENSE                                   # 许可证文件
│   ├── README.md                                 # 说明文档
│   ├── electron-builder.json                     # Electron打包配置
│   ├── package-lock.json                         # 包锁定文件
│   ├── package.json                              # 项目配置文件
│   ├── tsconfig.json                             # TS配置文件
│   └── vite.config.js                            # Vite配置文件
├── docs                                          # 文档目录
│   ├── image-2.png                               # 文档图片
│   └── image.png                                 # 文档图片
├── LICENSE                                       # 许可证文件
├── README.md                                     # 项目说明文档
└── project_tree.md                               # 项目目录结构说明
```
