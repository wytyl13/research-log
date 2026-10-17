"""compile.py — 确定性编译（v3）：三库 → 上下文卡.md（AI 系统提示词）+ 总览.md（人看）。

零 token，随时可重跑。库里状态全是文字；图标只在本模块渲染进总览。
所有路径通过 store.X 动态访问（selftest 可整体换到临时目录）。
"""
import datetime
import re

import store

ICON = {"建议中": "⬜", "已采纳": "✅", "已被取代": "🔄", "已废弃": "❌",
        "待验证": "⬜", "验证中": "🟨", "成立": "✅", "不成立": "❌", "搁置": "⏸",
        "未开始": "⬜", "进行中": "🟨", "已完成": "✅",
        "未读": "⬜", "在读": "🟨", "已读": "✅"}


def _icon(status):
    for k, v in ICON.items():
        if status.startswith(k):
            return v
    return ""


def _section(text, name):
    m = re.search(rf"^## {name}\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


# ---------- 解析 ----------

def load_adrs():
    out = []
    for f in sorted(store.D_DIR.glob("????-*.md")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"^# (\d+)\. (.+)$", t, re.M)
        if not m:
            continue
        d = re.search(r"^日期:\s*(.+)$", t, re.M)
        st = _section(t, "状态").splitlines()
        out.append(dict(num=int(m.group(1)), id=f"{int(m.group(1)):04d}", title=m.group(2).strip(),
                        file=f.stem, date=d.group(1).strip() if d else "",
                        status=st[0].strip() if st else "", decision=_section(t, "决定")))
    return out


def load_logbook():
    """全部条目（跨全部日文件），最新日在前、日内按出现顺序。"""
    out = []
    for f in sorted(store.P_DIR.glob("????-??-??.md"), reverse=True):
        t = f.read_text(encoding="utf-8")
        heads = list(store.ENTRY_HEAD.finditer(t))
        for i, m in enumerate(heads):
            block = t[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(t)]
            fields = {k.strip(): v.strip() for k, v in store.FIELD_LINE.findall(block)}
            out.append(dict(day=f.stem, id=m.group(1), letter=m.group(1)[0], title=m.group(2).strip(),
                            status=fields.get("状态", ""), fields=fields))
    return out


def load_cards():
    out = []
    for f in sorted(store.I_DIR.glob("*.md")):
        t = f.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", t, re.M)
        body = re.split(r"^# .+?$", t, maxsplit=1, flags=re.M)[1] if title else t
        body = re.split(r"^链接：", body, maxsplit=1, flags=re.M)[0].strip()
        out.append(dict(ts=f.stem[:12], file=f.stem, title=title.group(1).strip() if title else f.stem,
                        body=body.splitlines()[0] if body else ""))
    return sorted(out, key=lambda x: x["ts"], reverse=True)


# ---------- 生成 ----------

def _north():
    return store.NORTH.read_text(encoding="utf-8").strip() if store.NORTH.exists() else "（缺 方向.md）"


def _first(s):
    return s.splitlines()[0] if s else ""


def build_card():
    adrs = load_adrs()
    entries = load_logbook()
    cards = load_cards()
    acc = [a for a in adrs if a["status"] == "已采纳"]
    prop = [a for a in adrs if a["status"] == "建议中"]
    gone = [a for a in adrs if a["status"].startswith(("已被取代", "已废弃"))]
    L = []
    L.append("# 🎫 上下文卡\n")
    L.append("> 由 compile.py 从三库自动生成，勿手改。作系统提示词时从下一行起全选粘贴。\n")
    L.append("## 我在研究什么\n")
    L.append(_north() + "\n")
    L.append("## 已定的决策（不要动摇我）\n")
    for a in acc:
        L.append(f"- ADR-{a['id']} {a['title']}" + (f"——{_first(a['decision'])}" if a["decision"] else ""))
    L.append("")
    L.append("## 排队中的思路（建议中）\n")
    for a in prop:
        L.append(f"- ADR-{a['id']} {a['title']}" + (f"——{_first(a['decision'])}" if a["decision"] else ""))
    if gone:
        L.append("- 已取代/废弃：" + "；".join(f"ADR-{a['id']} {a['title']}（{a['status']}）" for a in gone))
    if not prop:
        L.append("-（暂无）")
    L.append("")
    L.append("## 实验与假设\n")
    for e in (x for x in entries if x["letter"] == "E"):
        dep = e["fields"].get("前置", "")
        L.append(f"- {e['id']} {e['title']}（{e['status']}，{e['day']}）" + (f" ← 前置 {dep}" if dep else ""))
    for h in (x for x in entries if x["letter"] == "H"):
        ve = h["fields"].get("验证实验", "")
        L.append(f"- {h['id']} {h['title']}（{h['status']}）" + (f" ← 由 {ve} 验证" if ve else ""))
    L.append("")
    reads = [x for x in entries if x["letter"] == "R"]
    if reads:
        L.append("## 阅读\n")
        for r in reads:
            note = r["fields"].get("收获", "")
            L.append(f"- {r['id']} {r['title']}（{r['status']}）" + (f"——{note}" if note else ""))
        L.append("")
    L.append("## 想法卡片（无状态，新在前）\n")
    for c in cards[:15]:
        L.append(f"- {c['title']}" + (f"：{c['body'][:60]}" if c["body"] else ""))
    L.append("")
    L.append("## 对 AI 的要求\n")
    L.append("延续以上状态讨论，不要重新发明方向。产生值得记录的新想法、决策或实验结果时，提醒我记录"
             "（实时用 MCP 工具 add_card / add_adr / set_status，或把材料丢进 inbox/ 等同步）。\n")
    return "\n".join(L)


def build_overview():
    adrs, entries, cards = load_adrs(), load_logbook(), load_cards()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = [f"# 📊 总览（编译于 {now}）\n"]

    def stat(items, key="status"):
        c = {}
        for x in items:
            k = next((w for w in store.ADR_STATUSES + store.HYP_STATUSES + store.EXP_STATUSES
                      + store.READ_STATUSES if x[key].startswith(w)), x[key] or "无状态")
            c[k] = c.get(k, 0) + 1
        return " ｜ ".join(f"{_icon(k)}{k}×{v}" for k, v in sorted(c.items())) or "空"

    L.append(f"- decisions：{len(adrs)} 条（{stat(adrs)}）")
    L.append(f"- 记录本条目：{len(entries)} 条 ｜ 实验 {sum(1 for e in entries if e['letter'] == 'E')}"
             f"（{stat([e for e in entries if e['letter'] == 'E'])}）"
             f"｜ 假设 {sum(1 for e in entries if e['letter'] == 'H')}"
             f"（{stat([e for e in entries if e['letter'] == 'H'])}）"
             f"｜ 阅读 {sum(1 for e in entries if e['letter'] == 'R')}")
    L.append(f"- ideas：{len(cards)} 张卡片\n")
    L.append("## 决策与思路（decisions/，严格 ADR）\n")
    L.append("| ID | 标题 | 状态 | 日期 |")
    L.append("|---|---|---|---|")
    for a in adrs:
        L.append(f"| ADR-{a['id']} | {a['title']} | {_icon(a['status'])} {a['status']} | {a['date']} |")
    L.append("")
    L.append("## 实验记录本（process/，按日）\n")
    L.append("| 日 | ID | 标题/假设 | 状态 | 关键字段 |")
    L.append("|---|---|---|---|---|")
    for e in entries:
        extra = e["fields"].get("结论") or e["fields"].get("收获") or e["fields"].get("验证实验") or ""
        L.append(f"| {e['day']} | {e['id']} | {e['title'][:60]} | {_icon(e['status'])} {e['status']} | {extra[:60]} |")
    L.append("")
    L.append("## 想法卡片（ideas/，Zettelkasten，新在前）\n")
    L.append("| 时间戳 | 标题 |")
    L.append("|---|---|")
    for c in cards:
        L.append(f"| {c['ts']} | {c['title']} |")
    return "\n".join(L)


def run():
    with store._Lock():
        store.CARD.write_text(build_card() + "\n", encoding="utf-8")
        store.OVERVIEW.write_text(build_overview() + "\n", encoding="utf-8")
    return f"已编译 {store.CARD.name} + {store.OVERVIEW.name}"


if __name__ == "__main__":
    print(run())
