# research-log MCP（三库版 v3）

让任何支持 MCP 的 AI 客户端（Cherry Studio / Claude Desktop / Claude Code）直接读写科研记录三库：
`decisions/`（严格 ADR）、`process/`（严格实验记录本，按日一文件）、`ideas/`（严格 Zettelkasten，无状态卡片）。
stdio 传输，单文件，无状态。写入后自动重编译 `上下文卡.md` 和 `总览.md`。

> 注意：这台机器的 `python` 命令是 Windows 商店假壳，**必须用完整路径**
> `C:/ProgramData/anaconda3/python.exe`

## 工具

| 工具 | 干什么 |
|---|---|
| `get_context()` | 返回上下文卡全文——新对话开始时调用，等于自动粘贴系统提示词 |
| `add_idea(标题, 正文, 链接)` | 往 ideas/ 追加一张卡片（无状态无归属） |
| `add_decision(标题, 背景, 决定, 后果, 状态, 依据)` | 新建 ADR，编号自动递增；状态：建议中/已采纳/已被取代/已废弃 |
| `add_experiment(标题, 假设, 方案, 前置)` | 往 process/ 今天的日文件登记实验，编号自动分配 |
| `set_status(目标, 状态, 备注)` | 改状态：adr-0005 / E2 / H1 / R1（想法卡片没有状态） |

## 成本与通道选择

| 通道 | 花谁的 token | 适用场景 |
|---|---|---|
| 聊天里让 AI 调 MCP | 当前对话的模型，单次一两百 token（旗舰价下不到一分钱） | 聊着聊着顺手记 |
| **批量导入聊天记录** | **不走本服务**：导出 → `inbox/` → `sync.py`（Haiku 提炼） | 非实时的默认路径 |
| CLI 模式 | **零 token**，不经过任何模型 | 不想让模型碰记录时 |

MCP 不做"导入/提炼"（那需要 LLM 读长材料做判断），长材料一律走 inbox + sync.py。

## CLI 零 token 通道

```
C:/ProgramData/anaconda3/python.exe C:/Users/weiyutao/20260823/continual_learning/research-mcp/server.py add-idea "想法标题" "一两句正文"
C:/ProgramData/anaconda3/python.exe C:/Users/weiyutao/20260823/continual_learning/research-mcp/server.py add-decision "决策标题" "背景" "决定" "后果" "已采纳" "依据"
C:/ProgramData/anaconda3/python.exe C:/Users/weiyutao/20260823/continual_learning/research-mcp/server.py set-status H1 验证中 "备注"
C:/ProgramData/anaconda3/python.exe C:/Users/weiyutao/20260823/continual_learning/research-mcp/server.py get-context
```

## 注册

**Cherry Studio**：设置 → MCP 服务器 → 添加
- 命令：`C:/ProgramData/anaconda3/python.exe`
- 参数：`C:/Users/weiyutao/20260823/continual_learning/research-mcp/server.py`

**Claude Desktop**（`%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "research-log": {
      "command": "C:/ProgramData/anaconda3/python.exe",
      "args": ["C:/Users/weiyutao/20260823/continual_learning/research-mcp/server.py"]
    }
  }
}
```

**Claude Code**：

```
claude mcp add research-log -- C:/ProgramData/anaconda3/python.exe C:/Users/weiyutao/20260823/continual_learning/research-mcp/server.py
```

## 在聊天里怎么用

- 「先调用 get_context 了解我的研究状态」
- 「把这个想法用 add_idea 记下来」
- 「刚才这个思路否了，用 set_status 把 adr-0005 改成 已废弃，备注原因」
