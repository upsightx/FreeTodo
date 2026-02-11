# FreeTodo 后端架构文档

## 1. 整体架构概览

```mermaid
graph TB
    subgraph Client["客户端层"]
        FE[Next.js 前端]
        EL[Electron 桌面端]
    end

    subgraph Server["FastAPI 服务层"]
        APP[FastAPI App<br/>server.py]
        MW[CORS 中间件]
        LF[Lifespan 生命周期]
    end

    subgraph Modules["模块注册系统"]
        MR[Module Registry<br/>模块注册器]
        PM[Priority Modules<br/>优先模块]
        DM[Deferred Modules<br/>延迟模块]
    end

    subgraph Routers["路由层 (API Endpoints)"]
        direction TB
        R_CORE[核心路由<br/>health, config, system]
        R_TODO[待办路由<br/>todo, todo_extraction]
        R_CHAT[对话路由<br/>chat, agent_plan]
        R_DATA[数据路由<br/>activity, event, screenshot]
        R_AI[AI 路由<br/>vision, rag, vector, ocr]
        R_AUTO[自动化路由<br/>automation, scheduler]
        R_OTHER[其他路由<br/>journal, notification, audio...]
    end

    subgraph Services["服务层"]
        SVC_TODO[TodoService]
        SVC_CHAT[ChatService]
        SVC_EVT[EventService]
        SVC_ACT[ActivityService]
        SVC_CFG[ConfigService]
        SVC_AUD[AudioService]
        SVC_JRN[JournalService]
    end

    subgraph LLM["LLM 服务层"]
        LLC[LLMClient<br/>统一客户端]
        RAG[RAGService]
        VEC[VectorService]
        AGN[AgnoAgent<br/>智能代理]
        TODO_EXT[TodoExtractionService]
        OCR_EXT[OCRTodoExtractor]
        AUTO_DET[AutoTodoDetectionService]
    end

    subgraph Jobs["后台任务层"]
        JM[JobManager<br/>任务管理器]
        SCH[Scheduler<br/>APScheduler]
        J_REC[Recorder<br/>屏幕录制]
        J_OCR[OCR 处理器]
        J_AGG[Activity Aggregator]
        J_TODO[Todo Recorder]
        J_POCR[Proactive OCR]
        J_DDL[DDL Reminder]
    end

    subgraph Storage["存储层"]
        DB[(SQLite<br/>lifetrace.db)]
        VDB[(ChromaDB<br/>向量数据库)]
        MGR_TODO[TodoManager]
        MGR_EVT[EventManager]
        MGR_SCR[ScreenshotManager]
        MGR_ACT[ActivityManager]
        MGR_OCR[OCRManager]
        MGR_CHAT[ChatManager]
    end

    subgraph Config["配置层"]
        CFG[config.yaml]
        DCFG[default_config.yaml]
        PROMPT[prompts/*.yaml]
    end

    %% 连接关系
    Client --> Server
    APP --> MW --> MR
    LF --> JM
    MR --> PM & DM
    PM & DM --> Routers
    Routers --> Services
    Services --> LLM
    Services --> Storage
    LLM --> LLC
    LLC --> RAG & VEC & AGN
    Jobs --> Storage
    JM --> SCH
    SCH --> J_REC & J_OCR & J_AGG & J_TODO & J_POCR & J_DDL
    Storage --> DB & VDB
    Config --> Services
```

---

## 2. 分层架构详解

### 2.1 路由层 (Routers)

```mermaid
graph LR
    subgraph Core["核心模块 (core=True)"]
        health["/api/health"]
        config["/api/config"]
        system["/api/system"]
    end

    subgraph Priority["优先加载"]
        todo["/api/todos"]
    end

    subgraph Deferred["延迟加载"]
        chat["/api/chat"]
        activity["/api/activity"]
        event["/api/events"]
        screenshot["/api/screenshots"]
        search["/api/search"]
        ocr["/api/ocr"]
        vector["/api/vector"]
        rag["/api/rag"]
        scheduler["/api/scheduler"]
        automation["/api/automation"]
        journal["/api/journal"]
        notification["/api/notifications"]
        vision["/api/vision"]
        audio["/api/audio"]
        floating["/api/floating-capture"]
        crawler["/api/crawler"]
        plugin["/api/plugin"]
    end
```

### 2.2 待办检测功能架构

```mermaid
flowchart TB
    subgraph Triggers["触发方式"]
        T1[todo_recorder_job<br/>白名单应用截图]
        T2[proactive_ocr_job<br/>主动 OCR 检测]
        T3[floating_capture<br/>悬浮窗截图]
        T4[audio_extraction<br/>音频转录提取]
    end

    subgraph Detection["检测模块"]
        D1[AutoTodoDetectionService<br/>VLM 视觉模型方式]
        D2[OCRTodoExtractor<br/>OCR + 文本 LLM 方式]
    end

    subgraph Processing["处理流程"]
        P1[截图/OCR文本]
        P2[LLM 分析]
        P3[去重检查]
        P4[创建 draft Todo]
    end

    subgraph Output["输出"]
        O1[Draft 待办]
        O2[前端轮询展示]
        O3[用户确认/拒绝]
    end

    T1 --> D1
    T2 --> D2
    T3 --> D1
    T4 --> D2

    D1 --> P1 --> P2 --> P3 --> P4 --> O1 --> O2 --> O3
    D2 --> P1
```

---

## 3. 后台任务系统

```mermaid
flowchart TB
    subgraph JobManager["JobManager 任务管理器"]
        START[start_all]
        STOP[stop_all]
    end

    subgraph SchedulerManager["APScheduler"]
        ADD[add_interval_job]
        PAUSE[pause_job]
        RESUME[resume_job]
    end

    subgraph Jobs["定时任务"]
        recorder_job["recorder_job<br/>屏幕录制<br/>interval: 5s"]
        ocr_job["ocr_job<br/>OCR 识别<br/>interval: 10s"]
        activity_aggregator_job["activity_aggregator_job<br/>活动聚合<br/>interval: 60s"]
        clean_data_job["clean_data_job<br/>数据清理<br/>interval: 3600s"]
        todo_recorder_job["todo_recorder_job<br/>Todo 专用录制<br/>interval: 5s"]
        proactive_ocr_job["proactive_ocr_job<br/>主动 OCR<br/>interval: 1s"]
        deadline_reminder_job["deadline_reminder_job<br/>DDL 提醒"]
        audio_recording_job["audio_recording_job<br/>音频录制状态检查"]
    end

    JobManager --> SchedulerManager
    SchedulerManager --> Jobs
```

---

## 4. 存储层架构

```mermaid
erDiagram
    TODOS {
        int id PK
        string name
        string description
        string status
        string priority
        datetime start_time
        datetime deadline
        datetime created_at
    }

    EVENTS {
        int id PK
        string event_type
        string app_name
        string window_title
        datetime timestamp
    }

    SCREENSHOTS {
        int id PK
        string file_path
        string file_hash
        int width
        int height
        datetime created_at
    }

    OCR_RESULTS {
        int id PK
        int screenshot_id FK
        string text_content
        string text_hash
        datetime created_at
    }

    ACTIVITIES {
        int id PK
        string title
        string summary
        datetime start_time
        datetime end_time
    }

    CHAT_MESSAGES {
        int id PK
        string session_id
        string role
        string content
        datetime created_at
    }

    JOURNAL_ENTRIES {
        int id PK
        date entry_date
        string content
        datetime created_at
    }

    TODOS ||--o{ SCREENSHOTS : "关联截图"
    SCREENSHOTS ||--o{ OCR_RESULTS : "OCR结果"
    EVENTS ||--o{ SCREENSHOTS : "触发截图"
    ACTIVITIES ||--o{ EVENTS : "聚合事件"
```

---

## 5. LLM 服务架构

```mermaid
flowchart TB
    subgraph LLMClient["LLMClient 统一客户端"]
        CHAT[chat<br/>文本对话]
        VISION[vision_chat<br/>视觉对话]
        STREAM[stream_chat<br/>流式对话]
        INTENT[意图识别]
        QUERY[查询改写]
    end

    subgraph Models["模型配置"]
        M1[model<br/>默认文本模型]
        M2[vision_model<br/>视觉模型]
        M3[embedding_model<br/>嵌入模型]
    end

    subgraph Services["AI 服务"]
        RAG[RAGService<br/>检索增强生成]
        VEC[VectorService<br/>向量检索]
        AGNO[AgnoAgent<br/>智能代理]
        TODO_EXT[TodoExtractionService<br/>待办提取]
        SEARCH[WebSearchService<br/>网络搜索]
    end

    Models --> LLMClient
    LLMClient --> Services
```

---

## 6. 配置热更新机制

```mermaid
sequenceDiagram
    participant FE as 前端
    participant API as /api/config
    participant CFG as ConfigService
    participant WATCH as ConfigWatcher
    participant JOB as JobManager

    FE->>API: PUT /api/config
    API->>CFG: save_config(data)
    CFG->>CFG: 写入 config.yaml
    CFG->>WATCH: 触发配置变更事件
    WATCH->>JOB: 根据配置启用/暂停任务
    Note over WATCH,JOB: 例如: jobs.auto_todo_detection.enabled<br/>→ 暂停/恢复 todo_recorder_job
```

---

## 7. 目录结构

```
lifetrace/
├── server.py              # FastAPI 入口
├── core/                  # 核心模块
│   ├── module_registry.py # 模块注册系统
│   ├── config_watcher.py  # 配置热更新
│   ├── dependencies.py    # 依赖注入
│   └── lazy_services.py   # 延迟加载服务
├── routers/               # API 路由层
│   ├── todo.py            # 待办管理
│   ├── chat/              # 对话模块
│   ├── automation.py      # 自动化任务
│   └── ...
├── services/              # 业务服务层
│   ├── todo_service.py
│   ├── chat_service.py
│   └── ...
├── llm/                   # LLM 相关
│   ├── llm_client.py      # 统一 LLM 客户端
│   ├── rag_service.py     # RAG 服务
│   ├── agno_agent.py      # Agno 智能代理
│   ├── auto_todo_detection_service.py  # VLM 待办检测
│   ├── ocr_todo_extractor.py           # OCR 待办提取
│   └── ...
├── jobs/                  # 后台任务
│   ├── job_manager.py     # 任务管理器
│   ├── recorder.py        # 屏幕录制
│   ├── todo_recorder.py   # Todo 专用录制
│   ├── proactive_ocr/     # 主动 OCR
│   └── ...
├── storage/               # 数据存储层
│   ├── database.py        # 数据库连接
│   ├── models.py          # ORM 模型
│   ├── todo_manager.py    # 待办管理器
│   └── ...
├── schemas/               # Pydantic 数据模型
├── config/                # 配置文件
│   ├── default_config.yaml
│   └── prompts/           # LLM 提示词
├── util/                  # 工具函数
└── migrations/            # 数据库迁移
```

---

## 8. 关键配置项

| 配置路径 | 说明 | 默认值 |
|----------|------|--------|
| `server.host` | 服务器地址 | `127.0.0.1` |
| `server.port` | 服务器端口 | `8001` |
| `llm.model` | 默认 LLM 模型 | - |
| `llm.vision_model` | 视觉模型 | - |
| `jobs.recorder.enabled` | 屏幕录制开关 | `false` |
| `jobs.auto_todo_detection.enabled` | 自动待办检测开关 | `false` |
| `jobs.proactive_ocr.enabled` | 主动 OCR 开关 | `false` |
| `jobs.proactive_ocr.params.auto_extract_todos` | OCR 文本待办提取 | `true` |
| `vector_db.enabled` | 向量数据库开关 | `true` |

---

## 9. API 端点汇总

| 模块 | 端点前缀 | 主要功能 |
|------|----------|----------|
| health | `/api/health` | 健康检查 |
| config | `/api/config` | 配置管理 |
| todo | `/api/todos` | 待办 CRUD |
| chat | `/api/chat` | AI 对话 |
| activity | `/api/activity` | 活动管理 |
| event | `/api/events` | 事件管理 |
| screenshot | `/api/screenshots` | 截图管理 |
| ocr | `/api/ocr` | OCR 识别 |
| vector | `/api/vector` | 向量操作 |
| rag | `/api/rag` | RAG 检索 |
| scheduler | `/api/scheduler` | 任务调度 |
| automation | `/api/automation` | 自动化任务 |
| journal | `/api/journal` | 日记管理 |
| notification | `/api/notifications` | 通知管理 |
| vision | `/api/vision` | 视觉分析 |
| audio | `/api/audio` | 音频处理 |
| floating_capture | `/api/floating-capture` | 悬浮窗截图 |
