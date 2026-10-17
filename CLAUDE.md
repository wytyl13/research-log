# 项目说明

本目录是科研项目 continual_learning 的工作区，含科研记录系统（v3 严格三标准版）。

- **唯一真相（三库，只增不删）**：
  - `decisions/` 严格 ADR：`NNNN-标题.md`，节式 日期/状态/背景/决定/后果/依据；状态用文字——建议中/已采纳/已被取代（ADR-NNNN）/已废弃
  - `process/` 严格实验记录本：按日一文件 `YYYY-MM-DD.md`，条目 `## E2 · 标题` + `- 字段: 值` 行；状态用文字（假设：待验证/验证中/成立/不成立/搁置；实验：未开始/进行中/已完成/搁置；阅读：未读/在读/已读）
  - `ideas/` 严格 Zettelkasten：`YYYYMMDDHHMM-标题.md` 原子卡片，**无状态无归属**，靠 `[[链接]]` 长出结构
- 图标只是 `compile.py` 渲染进总览的装饰，库内一律文字状态
- `上下文卡.md`、`总览.md` 由 `compile.py` 生成，勿手改
- **自动同步**：会话启动钩子后台跑 `sync.py`（新材料 → Haiku 提炼 → 入库 → 编译）；手动跑 `sync.py` 或 `/记日志`；聊天导出/笔记丢 `inbox/`
- `research-mcp/`：三库的 MCP 服务（实时单条记录），注册方式见其 README
- Python 必须用 `C:/ProgramData/anaconda3/python.exe`（`python` 命令是商店假壳）
- v2 旧库+旧代码在 `_archive/v2/`（含文件名对照表），另有 `_backup_v2/` 备份；git 已初始化
- 代码实现在 `continual_learning-main/`，与记录系统互相独立
