"""aggregate.py — 只读聚合：三库 → CONTEXT.md + OVERVIEW.md。

纯固定格式抽取，不调模型。CONTEXT 只装当前状态（刻意做小），
OVERVIEW 装全量（给人的浏览入口）。复用 store 的库根与链接扫描。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

import store

OPEN_ADR = ("建议中", "已采纳")
OPEN_ENTRY = {"E": ("未开始", "进行中", "搁置"),
              "H": ("待验证", "验证中", "搁置"),
              "R": ("未读", "在读")}
KIND_NAME = {"E": "实验", "H": "假设", "R": "阅读"}

_ENTRY_HEAD = re.compile(r"^## ([EHR])(\d+) · (.+)$", re.M)
_FIELD = re.compile(r"^- ([^:]+): (.*)$", re.M)


def _decisions() -> list[dict]:
    out = []
    for p in sorted(store.lib("decisions").glob("*.md")):
        if not p.stem.isdigit():
            continue
        text = p.read_text(encoding="utf-8")
        m = re.search(r"^# \d+\. (.+)$", text, re.M)
        d = re.search(r"^日期: (.+)$", text, re.M)
        s = re.search(r"^## 状态\s*\n\s*\n(.+)$", text, re.M)
        out.append({"num": int(p.stem),
                    "title": m.group(1) if m else p.stem,
                    "date": d.group(1) if d else "",
                    "status": s.group(1).strip() if s else ""})
    return out


def _entries() -> list[dict]:
    out = []
    for p in sorted(store.lib("logbook").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        heads = list(_ENTRY_HEAD.finditer(text))
        for i, m in enumerate(heads):
            block = text[m.start(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
            out.append({"kind": m.group(1), "num": int(m.group(2)), "title": m.group(3),
                        "day": p.stem, "fields": dict(_FIELD.findall(block))})
    return out


def _ideas() -> list[dict]:
    out = []
    for p in sorted(store.lib("ideas").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.search(r"^# (.+)$", text, re.M)
        out.append({"stamp": p.stem, "title": m.group(1) if m else p.stem,
                    "links": store._LINK_RE.findall(text)})
    return out


def _link_map(dec, ent, ids) -> dict[str, str]:
    lm = {f"{d['num']:04d}": f"records/decisions/{d['num']:04d}.md" for d in dec}
    lm.update({f"{e['kind']}{e['num']}": f"records/logbook/{e['day']}.md" for e in ent})
    lm.update({c["stamp"]: f"records/ideas/{c['stamp']}.md" for c in ids})
    return lm


def _md(ref: str, lm: dict[str, str]) -> str:
    # ponytail: 链接不带标题锚点，点开落文件头；文件大了再加锚点
    key = ref.strip().upper().replace("ADR-", "")
    return f"[{ref}]({lm[key]})" if key in lm else ref


def _related(e) -> str:
    keys = {"E": ("假设", "前置"), "H": ("验证实验",), "R": ("服务",)}[e["kind"]]
    return "、".join(v for k in keys if (v := e["fields"].get(k, "")))


def _inbox_n() -> int:
    d = store.lib("inbox")
    return len([p for p in d.iterdir() if p.is_file()]) if d.exists() else 0


def _context(dec, ent, ids, lm) -> str:
    now = datetime.now()
    L = ["# 研究当前状态（aggregate.py 自动聚合，勿手改）", "",
         f"> 生成 {now:%Y-%m-%d %H:%M}；完结条目与历史见 OVERVIEW.md", ""]

    L += ["## 决策主线", "", "| 编号 | 标题 | 状态 |", "| --- | --- | --- |"]
    rows = []
    for d in dec:
        if d["status"] in OPEN_ADR:
            num = f"{d['num']:04d}"
            rows.append(f"| {_md(num, lm)} | {d['title']} | {d['status']} |")
    L += rows or ["| （无） |  |  |"]
    L.append("")

    L += ["## 进行中（未完结的实验/假设/阅读）", "", "| 编号 | 标题 | 状态 | 关联 |",
          "| --- | --- | --- | --- |"]
    rows = []
    for e in ent:
        status = e["fields"].get("状态", "")
        if status in OPEN_ENTRY[e["kind"]]:
            eid = f"{e['kind']}{e['num']}"
            rows.append(f"| {_md(eid, lm)} | {e['title']} | {status} | {_related(e)} |")
    L += rows or ["| （无） |  |  |  |"]
    L.append("")

    week_ago = (now - timedelta(days=7)).strftime("%Y%m%d")
    recent = [c for c in ids if c["stamp"][:8] >= week_ago]
    L += [f"## 最近想法（近 7 天，全库 {len(ids)} 张）", ""]
    L += [f"- {_md(c['stamp'], lm)} {c['title']}" for c in recent] or ["- （无）"]
    L.append("")

    L += ["## 记录方式", "",
          "- 聊天中用 MCP 工具：add_* / set_status / fill_result / get",
          "- 命令行：`cli.py <子命令>`（零 token）",
          "- 外部材料放 `inbox/`，在 Claude Code 敲 `/import` 批量提炼", ""]
    return "\n".join(L)


def _overview(dec, ent, ids, lm, inbox_n) -> str:
    L = ["# 库总览（aggregate.py 自动聚合，勿手改）", "",
         f"> 生成 {datetime.now():%Y-%m-%d %H:%M} · 决策 {len(dec)} · "
         + " · ".join(f"{KIND_NAME[k]} {sum(1 for e in ent if e['kind'] == k)}"
                      for k in "EHR")
         + f" · 卡片 {len(ids)} · inbox 待处理 {inbox_n}", ""]

    L += ["## 决策", "", "| 编号 | 标题 | 状态 | 日期 |", "| --- | --- | --- | --- |"]
    rows = []
    for d in dec:
        num = f"{d['num']:04d}"
        rows.append(f"| {_md(num, lm)} | {d['title']} | {d['status']} | {d['date']} |")
    L += rows or ["| （无） |  |  |  |"]
    L.append("")

    for k in "EHR":
        L += [f"## {KIND_NAME[k]}", "", "| 编号 | 标题 | 状态 | 日期 | 关联 |",
              "| --- | --- | --- | --- | --- |"]
        rows = []
        for e in ent:
            if e["kind"] == k:
                eid = f"{e['kind']}{e['num']}"
                rows.append(f"| {_md(eid, lm)} | {e['title']} | "
                            f"{e['fields'].get('状态', '')} | {e['day']} | {_related(e)} |")
        L += rows or ["| （无） |  |  |  |  |"]
        L.append("")

    L += ["## 卡片", "", "| 卡片 | 标题 | 链接 |", "| --- | --- | --- |"]
    L += [f"| {_md(c['stamp'], lm)} | {c['title']} | {' '.join(_md(x, lm) for x in c['links'])} |"
          for c in ids] or ["| （无） |  |  |"]
    L.append("")

    L += ["## 引用索引（谁引用了谁）", ""]
    idx = store.scan_links()
    L += [f"- {_md(t, lm)} ← {'、'.join(f'[{s}]({s})' for s in srcs)}"
          for t, srcs in sorted(idx.items())] or ["- （无）"]
    L.append("")
    return "\n".join(L)


def run() -> dict:
    """聚合三库写出 CONTEXT.md 与 OVERVIEW.md，返回统计数。"""
    dec, ent, ids = _decisions(), _entries(), _ideas()
    lm = _link_map(dec, ent, ids)
    inbox = _inbox_n()
    store._write(store.ROOT / "CONTEXT.md", _context(dec, ent, ids, lm))
    store._write(store.ROOT / "OVERVIEW.md", _overview(dec, ent, ids, lm, inbox))
    return {"decisions": len(dec), "entries": len(ent), "ideas": len(ids), "inbox": inbox}
