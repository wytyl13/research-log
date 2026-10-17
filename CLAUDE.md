# 项目说明

本目录是科研项目 continual_learning 的工作区，含科研记录系统（v2 三库版）。

- **唯一真相**：`decisions/`（ADR：决策与实现思路）、`process/`（实验记录本：假设/实验/阅读/周志，按月一文件）、`ideas/`（想法卡片，Obsidian 兼容）。三库只增不删
- `上下文卡.md`、`总览.md` 由 `compile.py` 生成，勿手改
- **自动同步**：会话启动钩子后台跑 `sync.py`（新材料 → Haiku 提炼 → 入库 → 编译）；手动跑 `python sync.py` 或 `/记日志`；聊天导出/笔记丢 `inbox/`
- `research-mcp/`：三库的 MCP 服务（实时单条记录），注册方式见其 README
- Python 必须用 `C:/ProgramData/anaconda3/python.exe`（`python` 命令是商店假壳）
- 代码实现在 `continual_learning-main/`，与记录系统互相独立
