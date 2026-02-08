---
name: FreeTodo 插件系统标准化落地计划
overview: 将现有“模块注册+懒加载”升级为统一的前后端插件系统，支持插件生命周期管理、安装卸载、状态可观测、第三方扩展；并将 MediaCrawler 作为首个完整接入样板。
todos:
  - id: phase0-baseline
    content: "阶段0：梳理现状与兼容约束，冻结插件核心接口"
    status: pending
  - id: phase1-backend-kernel
    content: "阶段1：实现后端插件内核（接口、管理器、生命周期）"
    status: pending
  - id: phase2-backend-installation
    content: "阶段2：实现插件安装/卸载/状态 API 与安全校验"
    status: pending
  - id: phase3-frontend-runtime
    content: "阶段3：实现前端插件运行时与插件中心 UI"
    status: pending
  - id: phase4-mediacrawler-sample
    content: "阶段4：将 MediaCrawler 以标准插件方式接入"
    status: pending
  - id: phase5-hardening
    content: "阶段5：补齐测试、回滚策略、文档与发布流程"
    status: pending
isProject: false
---

# FreeTodo 插件系统标准化落地计划（高保真版）

## 1. 背景与问题定义

当前仓库已经具备“轻量插件化”的基础能力：

- 后端：`module_registry` 支持模块开关、依赖检测、按需注册路由。
- 前端：`registry.ts` 支持面板懒加载，结合 capabilities 做功能降级。

但这仍然不是完整插件系统，核心缺口如下：

1. **插件模型不统一**：前端面板、后端服务、Agent 工具没有统一插件定义。
2. **生命周期不完整**：只有 include_router，没有 startup/shutdown/health hooks。
3. **缺少安装能力**：没有标准的下载、校验、安装、卸载、升级机制。
4. **缺少插件中心**：前端无法统一管理插件状态、权限、版本、错误恢复。
5. **缺少第三方扩展协议**：没有插件清单规范（manifest）与目录约定。

因此，目标不是“给 MediaCrawler 打补丁”，而是先建设标准插件平台，再将 MediaCrawler 作为首个样板插件接入。

---

## 2. 目标与非目标

### 2.1 目标（Must Have）

1. 建立统一插件协议，覆盖三类插件：
   - `PanelPlugin`（前端面板插件）
   - `BackendPlugin`（后端服务插件）
   - `AgentToolPlugin`（Agent 工具插件）
2. 提供后端插件管理内核：发现、启停、依赖解析、生命周期、状态报告。
3. 提供插件安装能力：下载、哈希校验、解压、安装、卸载、回滚。
4. 提供前端插件运行时和插件中心：可视化管理与错误引导。
5. MediaCrawler 作为第一批“标准插件”接入，去除业务特判。

### 2.2 非目标（Not in Scope）

1. 本期不做“任意远程代码执行型插件市场”。
2. 本期不做跨进程沙箱（如 WASM 沙箱）落地，仅预留接口。
3. 本期不追求热替换（hot reload）复杂能力，以“重启生效+局部即时生效”优先。

---

## 3. 插件系统目标架构

```text
Plugin Platform
├── Shared Contract
│   ├── PluginManifest (JSON)
│   ├── DependencyGraph (plugin/module/tool)
│   └── Capability Model (state/health/errors)
├── Backend Runtime
│   ├── PluginManager
│   ├── BuiltinPluginAdapter (兼容现有 module_registry)
│   ├── InstallationService
│   └── Plugin APIs (/api/plugins/*)
├── Frontend Runtime
│   ├── Plugin Registry (static + server metadata)
│   ├── Lazy Loader / Install CTA / Error Boundaries
│   └── Plugin Center (enable/install/uninstall/diagnose)
└── First-party Sample Plugin
    └── media-crawler
```

---

## 4. 统一插件契约（Contract）

## 4.1 Manifest（建议）

每个插件目录包含 `plugin.manifest.json`，最小结构：

```json
{
  "id": "media-crawler",
  "name": "Media Crawler",
  "version": "1.0.0",
  "kind": ["backend", "panel"],
  "entry": {
    "backend": "plugin.py:plugin",
    "panel": "crawler-panel"
  },
  "dependencies": {
    "plugins": [],
    "modules": ["plugin"],
    "python": ">=3.11"
  },
  "permissions": ["network", "filesystem:data/plugins/media-crawler"],
  "integrity": {
    "sha256": "..."
  }
}
```

## 4.2 生命周期

统一状态机：

`discovered -> installed -> enabled -> starting -> running -> degraded -> stopped`

关键钩子：

- `validate()`：环境与依赖检查
- `startup(context)`：注册路由/任务/工具
- `healthcheck()`：运行时健康检查
- `shutdown()`：释放资源

## 4.3 兼容策略

为避免大改导致回归，保留 `backend_modules.*` 并提供适配层：

- `backend_modules` 继续生效；
- 内核将其映射为 builtin plugins 的启停配置；
- 新配置统一收敛到 `plugins.*`。

---

## 5. 后端设计（FastAPI / Python）

## 5.1 目录与文件建议

```text
lifetrace/
├── plugins/
│   ├── base.py                  # 插件基类与协议
│   ├── models.py                # manifest/state/dependency 数据模型
│   ├── manager.py               # 核心管理器（发现、启停、状态）
│   ├── installer.py             # 安装/卸载/升级/校验
│   ├── discovery.py             # 扫描 builtin + third-party
│   └── builtin/
│       ├── module_adapter.py    # 兼容现有 module_registry
│       └── media_crawler/
│           └── plugin.py
├── routers/
│   └── plugin.py                # /api/plugins/*
└── core/
    └── module_registry.py       # 逐步收敛为 adapter 输入
```

## 5.2 插件管理器职责

`PluginManager` 负责：

1. 发现插件（builtin + configured third-party dirs）。
2. 加载 manifest 与 entry，构建依赖图。
3. 根据配置启停插件并维护状态。
4. 对外提供状态快照（供 `/api/plugins`、`/api/capabilities`）。
5. 暴露统一错误码（安装失败、依赖缺失、启动失败、权限不足）。

## 5.3 插件 API（建议）

```text
GET    /api/plugins
GET    /api/plugins/{id}
POST   /api/plugins/{id}/enable
POST   /api/plugins/{id}/disable
POST   /api/plugins/{id}/install
POST   /api/plugins/{id}/uninstall
GET    /api/plugins/{id}/events      # SSE: 安装/升级进度
GET    /api/plugins/{id}/health
```

同时扩展 `/api/capabilities`：

```json
{
  "modules": { "enabled": [], "available": [], "missing_deps": {} },
  "plugins": { "enabled": [], "installed": [], "degraded": [], "errors": {} }
}
```

## 5.4 安全要求（最低标准）

1. 下载包必须做 `sha256` 校验。
2. 解压防 Zip Slip（禁止 `../` 逃逸）。
3. 安装过程加文件锁，防并发安装。
4. 失败自动回滚到上一个可用版本。
5. 插件目录限制在 `data/plugins/` 下，不允许任意路径写入。

---

## 6. 前端设计（Next.js / React）

## 6.1 运行时升级

现有 `lib/plugins/registry.ts` 为静态注册，升级为“双源模型”：

1. `staticRegistry`：内置面板定义（保留类型安全与懒加载）。
2. `serverRegistry`：来自 `/api/plugins` 的状态与元信息。
3. `resolvedRegistry`：融合后用于 UI 渲染与禁用策略。

## 6.2 插件中心（Settings）

新增“插件中心”分区，至少包含：

- 插件列表（已安装/未安装/已启用/异常）
- 安装与卸载按钮
- 版本与大小信息
- 错误诊断（依赖缺失、校验失败、运行异常）

## 6.3 面板插件 UX 约束

当插件面板未安装或不可用时，统一显示：

1. 价值说明（为什么要安装）
2. 安装按钮 + 进度 + 取消/重试
3. 错误信息 + 修复建议

这套 UX 不只服务 MediaCrawler，而是所有 panel 插件复用。

---

## 7. 配置设计

`lifetrace/config/default_config.yaml` 增加：

```yaml
plugins:
  enabled: []
  disabled: []
  install_dir: data/plugins
  third_party_dirs: []
  registries:
    - name: official
      base_url: https://example.com/releases/plugins
      enabled: true
  security:
    enforce_checksum: true
    allow_unsigned: false
```

兼容层：

- 读取 `backend_modules.enabled/disabled/unavailable`；
- 在运行时映射到 builtin plugin 状态；
- 逐步在设置页引导用户迁移到 `plugins.*`。

---

## 8. MediaCrawler 接入规范（作为样板插件）

## 8.1 插件包结构

```text
media-crawler-v1.0.0.zip
├── plugin.manifest.json
├── MediaCrawlerPro-Python/
├── MediaCrawlerPro-SignSrv/
└── adapter/
    └── plugin.py
```

## 8.2 后端接入原则

1. 不允许硬编码仓库同级目录路径。
2. 统一通过 `PluginManager.get_install_path("media-crawler")` 获取根目录。
3. `crawler` 路由只依赖插件能力，不直连固定目录常量。
4. 插件未安装时返回标准错误码（如 `PLUGIN_NOT_INSTALLED`）。

## 8.3 前端接入原则

1. `CrawlerPanel` 走统一插件面板 fallback。
2. 安装逻辑通过 `/api/plugins/media-crawler/install`。
3. 进度通过 SSE 或 polling，不自行维护多套状态协议。

---

## 9. 分阶段实施计划（可执行）

## 阶段 0：现状固化与契约冻结（0.5-1 天）

**目标**：冻结接口，避免边做边改。

任务：

1. 定义 `PluginManifest`、`PluginState`、`PluginErrorCode`。
2. 明确 `BackendPlugin` / `PanelPlugin` / `AgentToolPlugin` 协议。
3. 输出兼容映射表（旧 module -> builtin plugin）。

验收：

- 接口文档评审通过；
- 兼容策略有明确迁移说明。

## 阶段 1：后端插件内核（2-3 天）

**目标**：跑通“发现 -> 启停 -> 状态”。

任务：

1. 新增 `lifetrace/plugins/base.py`、`models.py`、`manager.py`。
2. 实现 builtin module adapter，复用现有模块路由能力。
3. 在 `server.py` 中由 `PluginManager` 驱动启动流程。

验收：

- 原有功能不回归；
- `/api/capabilities` 可输出插件态信息。

## 阶段 2：安装与插件 API（2-3 天）

**目标**：跑通“安装 -> 启用 -> 卸载 -> 回滚”。

任务：

1. 新增 `installer.py`（下载、哈希、解压、回滚、锁）。
2. 新增 `routers/plugin.py` 与标准 API。
3. 配置新增 `plugins.*` 并加入 settings validator。

验收：

- 模拟损坏 zip 时能失败并回滚；
- 并发安装请求不会破坏目录。

## 阶段 3：前端运行时与插件中心（2-3 天）

**目标**：用户可在 UI 管理插件全生命周期。

任务：

1. `lib/plugins/registry.ts` 改为静态+服务端融合。
2. 新增插件中心页（列表、安装、卸载、诊断）。
3. 统一插件面板 fallback 组件。

验收：

- 插件状态与后端一致；
- 安装失败信息可见且可重试。

## 阶段 4：MediaCrawler 样板接入（2-4 天）

**目标**：以标准插件方式接入，不留业务特判。

任务：

1. 创建 `media-crawler` manifest 与 backend adapter。
2. 把 crawler 路由路径解析改为插件目录解析。
3. CrawlerPanel 接入统一插件安装与状态流。

验收：

- 未安装时面板显示引导；
- 安装后可启动；
- 卸载后状态恢复为未安装。

## 阶段 5：稳定性与发布（1-2 天）

**目标**：可持续交付。

任务：

1. 加入关键测试（安装器、依赖图、状态机、API）。
2. 增加发布脚本（插件打包、checksum 生成、manifest 校验）。
3. 输出运维手册（故障排查、回滚流程、日志定位）。

验收：

- CI 至少覆盖核心插件路径；
- 文档可指导新成员独立接入第二个插件。

---

## 10. 验收标准（Definition of Done）

满足以下条件才算插件系统落地：

1. 三类插件协议已落地并被主流程使用。
2. 内置模块由插件内核统一管理（至少通过 adapter）。
3. 插件可安装/卸载/启停，且失败可回滚。
4. 前端有统一插件中心，并能展示运行态与错误态。
5. MediaCrawler 通过标准插件路径接入，不存在硬编码路径依赖。
6. 新增任一插件时，不需要修改核心框架文件（仅注册与实现）。

---

## 11. 风险与应对

1. **风险：一次性改造过大导致回归**
   - 应对：先 adapter 化，后逐步替换旧路径。
2. **风险：插件安装失败率高**
   - 应对：checksum + 断点重试 + 回滚 + 错误码标准化。
3. **风险：前后端状态不一致**
   - 应对：单一状态源（后端），前端仅消费 API。
4. **风险：第三方插件安全边界不足**
   - 应对：首期只开放官方 allowlist，第三方默认关闭。

---

## 12. 推荐执行顺序

建议按以下顺序推进，避免并行冲突：

1. 先完成阶段 0 + 1（内核），
2. 再做阶段 2（安装与 API），
3. 然后阶段 3（前端中心），
4. 最后阶段 4（MediaCrawler 接入）。

不要先做 MediaCrawler 特化实现，否则很容易再次形成“一次性逻辑”。
