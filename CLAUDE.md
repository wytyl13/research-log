# 项目说明

> 修改规则见 skill `doc-roles`：文档分工/环境约定段非用户明示不可改；
> 项目事实与当前进度段随项目状态更新。

## 文档分工

- 通用项目规则在 `.claude/skills/`（17 条），改任何文件前先读相关规则
- `DESIGN.md`：本项目唯一设计与规划文件（设计/规划/进度/决策）
- `README.md`：稳定的项目说明，收口时按 `readme-structure` 定稿

## 环境约定

- Python 用 conda 环境

## 项目事实与当前进度（项目独有，随进度更新）

- 科研记录系统 v4 已完成（2026-10-17，六步全部收口）：用法见 `README.md`，
  设计与全部决策见 `DESIGN.md`
- 记录三通道：聊天（MCP，`research_mcp.py`）/ 命令行（`cli.py`，零 token）/
  外部材料（`inbox/` + `/import` 命令）
- 旧版存档：v3 → `_backup_v3/` + git 标签 `v3-final`；更早 → `_backup_v2/`、`_archive/`
- `continual_learning-main/`：ML 代码实现，独立项目（当前工作区缺失，
  完整版在 git 标签 `v3-final` 里，待用户核实去向）
