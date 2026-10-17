---
description: 批量提炼 inbox/ 里的外部材料入库，完成后归档到 processed/
allowed-tools: Bash(C:/ProgramData/anaconda3/python.exe:*), Bash(mv:*), Read, Glob
---

按以下固定流程处理 `inbox/` 里的外部材料（笔记/日记/与其它 AI 的会话记录）：

## 1. 清点

列出 `inbox/` 下所有文件；为空则报告"inbox 为空"并结束。

## 2. 提炼候选

逐个读材料，提炼成五类记录的候选：决策（adr）/ 实验（exp）/ 假设（hyp）/ 阅读（read）/ 想法卡片（idea）。

提炼原则：

- 只保留材料里的事实与结论，不编造
- 材料里信息不足的字段留空
- 同一份材料里反复提到的同一件事合并为一条
- 实验与假设的关联用编号参数带上（如 `--hypothesis H1`）

## 3. 给用户确认（必停点）

把候选清单列表给用户：类型 / 标题 / 关键内容一句 / 出自哪份材料。
**等用户确认或修改后才继续；用户没点头，一条都不写。**

## 4. 写入

在仓库根目录逐条执行（格式受控，状态必须取自固定枚举）：

```
C:/ProgramData/anaconda3/python.exe -X utf8 cli.py <子命令> --title "..." ...
```

- `adr`：`--title --status(建议中/已采纳/已被取代/已废弃) --context --decision --consequence --basis`
- `exp`：`--title --status(未开始/进行中/已完成/搁置) --hypothesis --plan --prior`
- `hyp`：`--title --status(待验证/验证中/成立/不成立/搁置) --verify`
- `read`：`--title --status(未读/在读/已读) --serves`
- `idea`：`--title --text --link`（--link 可重复）

## 5. 归档

已处理的材料移入 `processed/`：`mv inbox/<文件> processed/`，
然后跑一次 `C:/ProgramData/anaconda3/python.exe -X utf8 cli.py build` 让统计归零。

## 6. 报告

报告本次新增的编号清单 + 一句统计，并说明 CONTEXT.md / OVERVIEW.md 已自动刷新。
