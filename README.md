# 科研记录系统（v4）

## 1. 背景

> 一段话说清本项目做什么、输入是什么、输出是什么。

把研究中的决策、实验与假设、阅读、想法记成只增不删的 Markdown 记录。输入：聊天内容、笔记、日记、与其它 AI 的会话记录。输出：三库记录 + `CONTEXT.md`（给 AI 的开局状态）+ `OVERVIEW.md`（给人的全貌）。设计与全部决策见 `DESIGN.md`。

## 2. Quick Start

> 环境、初始化、三个记录入口、自测命令，全部可直接复制执行。

- 环境：Windows；Python 用 conda：`C:/ProgramData/anaconda3/python.exe`（下文记作 `<py>`）；MCP 入口需 `mcp` 包（`<py> -m pip install mcp`，已装则跳过）。

初始化（建齐五目录并生成两份聚合文件，可重复执行）：

```bash
<py> -X utf8 cli.py build
```

三个记录入口：

| 入口 | 用法 | token |
| :--- | :--- | :--- |
| 聊天（MCP） | 在已注册的客户端里说"记一条实验……"，模型调工具写入 | 花 |
| 命令行 | `<py> -X utf8 cli.py exp --title "五任务准确率" --hypothesis H1` | 不花 |
| 外部材料 | 材料丢 `inbox/`，在 Claude Code 敲 `/import`，提炼清单确认后入库 | 花 |

MCP 注册（三处任选，`research_mcp.py` 用绝对路径）：

- Claude Code：
  ```bash
  claude mcp add research-log -- C:/ProgramData/anaconda3/python.exe C:/Users/weiyutao/20260823/continual_learning/research_mcp.py
  ```
- Claude Desktop（`claude_desktop_config.json`）：
  ```json
  {
    "mcpServers": {
      "research-log": {
        "command": "C:/ProgramData/anaconda3/python.exe",
        "args": ["C:/Users/weiyutao/20260823/continual_learning/research_mcp.py"]
      }
    }
  }
  ```
- Cherry Studio：设置 → MCP 服务 → 新建：命令 `C:/ProgramData/anaconda3/python.exe`，参数 `C:/Users/weiyutao/20260823/continual_learning/research_mcp.py`。

自测（四个脚本，各自独立跑）：

```bash
<py> -X utf8 test_store.py && <py> -X utf8 test_aggregate.py && <py> -X utf8 test_cli.py && <py> -X utf8 test_mcp.py
```

## 3. 架构

> 分层图与各层职责，依赖单向自上而下。

```
入口层    cli.py（命令行）   research_mcp.py（MCP）   /import 命令（模型调 cli）
              │                    │                        │
核心层         └──────────►  store.py（唯一写入口） ◄─────────┘
                                │
数据层        decisions/  logbook/  ideas/   ◄── aggregate.py（只读聚合）
```

| 模块 | 职责 | 编写规则 |
| :--- | :--- | :--- |
| `store.py` | 四种合法写入动作、编号分配、编号定位、引用扫描 | `.claude/skills/code-function` 等 |
| `aggregate.py` | 固定格式抽取聚合成两份文件 | 同上 |
| `cli.py` / `research_mcp.py` | 参数转译，不含逻辑 | 同上 |
| 文档 | README/DESIGN/CLAUDE 分工与更新权限 | `.claude/skills/doc-roles` |

## 4. 记录到聚合的全流程

> 材料/聊天 → store 写入三库 → aggregate 聚合 → 两份汇总文件。

| 步骤 | 输入 | 中间处理 | 输出 | 模块 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 聊天一句话 / CLI 参数 / `inbox/` 材料 | 组织成五类记录的字段 | 记录字段 | 入口层 |
| 2 | 记录字段 | 分配编号，按四种合法动作写入 | 三库文件 | `store.py` [1] |
| 3 | 三库文件 | 固定格式抽取、链接解析、反向索引 | `CONTEXT.md` / `OVERVIEW.md` | `aggregate.py` [2] |
| 4 | `CONTEXT.md` | 新会话开局喂给 AI | 当前研究状态 | 使用者 |
| 可选 | `inbox/` 材料 | `/import` 提炼入库后移动文件 | `processed/` 归档 | `/import` [5] |

## 5. 分实体明细：五类记录

> 每类记录的描述、约束、成本与输入输出。

| 类型 | 库 | 编号 | 通道 |
| :--- | :--- | :--- | :--- |
| 决策（ADR） | `decisions/` | `0001` | 三通道均可 |
| 实验（E） | `logbook/` | `E1` | 三通道均可 |
| 假设（H） | `logbook/` | `H1` | 三通道均可 |
| 阅读（R） | `logbook/` | `R1` | 三通道均可 |
| 想法卡片 | `ideas/` | 时间戳 | 三通道均可 |

- **决策**：描述：做了什么方向/技术决定。约束：状态只能取 建议中/已采纳/已被取代/已废弃；只增不删。成本：聊天与 `/import` 花 token，命令行不花。输入数据：标题、背景、决定、后果、依据。输出数据：`decisions/NNNN.md` 与 `OVERVIEW.md` 表中一行。
- **实验**：描述：验证什么、怎么验。约束：状态只能取 未开始/进行中/已完成/搁置；编号全局递增。成本：同上。输入数据：标题、假设编号、方案、前置。输出数据：记录本条目与表中一行，`fill_result` 回填结果/结论。
- **假设**：描述：一句话可证伪表述。约束：状态只能取 待验证/验证中/成立/不成立/搁置。成本：同上。输入数据：标题、验证实验编号。输出数据：记录本条目与表中一行。
- **阅读**：描述：读了什么、对哪条线有用。约束：状态只能取 未读/在读/已读。成本：同上。输入数据：标题、服务对象。输出数据：记录本条目与表中一行。
- **想法卡片**：描述：零散点子。约束：无状态、无归属，靠 `[[编号]]` 链接串联。成本：同上。输入数据：标题、正文、链接。输出数据：卡片文件与表中一行。

## 6. 汇总输出

> 每个输出文件一行。

| 文件名 | 内容 | 产出模块 |
| :--- | :--- | :--- |
| `CONTEXT.md` | 给 AI 的当前研究状态，只装未完结条目与近 7 天卡片 | `aggregate.py` |
| `OVERVIEW.md` | 给人看的全量总览：统计、三库全表、引用索引、inbox 待处理数 | `aggregate.py` |
| `decisions/` `logbook/` `ideas/` | 三库记录文件 | `store.py` |

## 7. 接口：MCP 工具

> 八个工具的传参与返回，均给最小示例。

| 工具 | 传参示例 | 返回示例 |
| :--- | :--- | :--- |
| `add_decision` | `title="冻结慢权重为主线", status="已采纳"` | `已记录决策 0001` |
| `add_experiment` | `title="五任务准确率", hypothesis="H1"` | `已记录实验 E1` |
| `add_hypothesis` | `title="冻结可降低遗忘"` | `已记录假设 H1` |
| `add_reading` | `title="某论文", serves="H1"` | `已记录阅读 R1` |
| `add_idea` | `title="分段冻结", text="只更新快权重", links=["0001"]` | `已记录卡片 202610172359` |
| `set_status` | `ref="E1", new_status="已完成"` | `E1 状态已改为 已完成` |
| `fill_result` | `ref="E1", result="+12%", conclusion="冻结有效"` | `E1 已回填结果/结论` |
| `get` | `ref="E1"` | 该条记录原文 |

命令行子命令与 MCP 工具一一对应（`adr/exp/hyp/read/idea/status/result/build`），速查见 Quick Start 与 `DESIGN.md` §5.1。

## 8. Reference

> 编号引用映射表。

`<!-- 核心 store.py -->`

- [1] `store.py`：`add_*` / `set_status` / `fill_result` / `resolve` / `scan_links`
- [2] `aggregate.py`：`run()`

`<!-- 入口层 -->`

- [3] `cli.py`：`main()`（八个子命令）
- [4] `research_mcp.py`：八个 `@mcp.tool()`
- [5] `.claude/commands/import.md`：`/import` 六步流程
