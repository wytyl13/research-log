"""compile.py — 确定性编译：三库 → 上下文卡.md（AI 系统提示词）+ 总览.md（人看的）。

零 token，随时可重跑。所有路径通过 store.X 动态访问（selftest 可整体换到临时目录）。
"""
import datetime
import re

import store


# ---------- 解析 ----------

def load_adrs():
    out = []
    for f in sorted(store.D_DIR.glob("adr-*.md")):
        m = re.match(r"adr-(\d+)", f.name)
        if not m:
            continue
        t = f.read_text(encoding="utf-8")

        def field(name):
            r = re.search(rf"^-\s*{name}\s*:\s*(.*)$", t, re.M)
            return r.group(1).strip() if r else ""
        title = re.search(r"^#\s+ADR-\d+\s*[:：]\s*(.+)$", t, re.M)
        out.append(dict(
            id=f"adr-{int(m.group(1)):03d}",
            title=title.group(1).strip() if title else f.stem,
            status=field("状态") or "⬜", date=field("日期"),
            decision=field("决定") or field("背景"), basis=field("依据")))
    return out


def load_process():
    """返回 {month: {hyps, reads, exps}}，倒序（最新月在前）。"""
    out = []
    for f in sorted(store.P_DIR.glob("*.md"), reverse=True):
        t = f.read_text(encoding="utf-8")
        hyps = [dict(id=m.group(1), text=m.group(2).strip(), exp=m.group(3).strip(), status=m.group(4))
                for m in re.finditer(r"^\|\s*(H\d+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(\S+)\s*\|", t, re.M)]
        reads = [dict(id=m.group(1), material=m.group(2).strip(), serves=m.group(3).strip(),
                      status=m.group(4), note=m.group(5).strip())
                 for m in re.finditer(r"^\|\s*(R\d+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(\S+)\s*\|\s*(.*?)\s*\|", t, re.M)]
        exps = []
        for m in re.finditer(r"^###\s+(\d{4}-\d{2}-\d{2})\s+(E\d+)\s*[:：]\s*(.+?)\s*([⬜🟨🟡✅❌⏸🔄⬆️])?\s*$", t, re.M):
            eid = m.group(2)
            tail = t[m.end():m.end() + 600]
            hyp = re.search(r"^-\s*假设:\s*(.+)$", tail, re.M)
            dep = re.search(r"^-\s*前置:\s*(.+)$", tail, re.M)
            concl = re.search(r"^-\s*结论:\s*(.+)$", tail, re.M)
            exps.append(dict(date=m.group(1), id=eid, title=m.group(3).strip(),
                             status=m.group(4) or "⬜", hypothesis=hyp.group(1).strip() if hyp else "",
                             depends=dep.group(1).strip() if dep else "",
                             conclusion=concl.group(1).strip() if concl else ""))
        out.append(dict(month=f.stem, hyps=hyps, reads=reads, exps=exps))
    return out


def load_ideas():
    out = []
    for f in sorted(store.I_DIR.glob("*.md")):
        t = f.read_text(encoding="utf-8")
        fm = t.split("---")[1] if t.startswith("---") else ""

        def fmfield(k, default=""):
            r = re.search(rf"^{k}\s*:\s*(.*)$", fm, re.M)
            return r.group(1).strip().strip('"') if r else default
        title = re.search(r"^#\s+(.+)$", t, re.M)
        out.append(dict(id=fmfield("id", "0"), file=f.stem, title=title.group(1).strip() if title else f.stem,
                        status=fmfield("status", "🟡"), date=fmfield("date"),
                        owner=fmfield("owner"), body=t.split("---", 2)[-1].strip().splitlines()[:1]))
    return sorted(out, key=lambda x: int(x["id"]) if x["id"].isdigit() else 0)


# ---------- 生成 ----------

def _north():
    if store.NORTH.exists():
        return store.NORTH.read_text(encoding="utf-8").strip()
    return "（缺 方向.md）"


def build_card():
    adrs = load_adrs()
    months = load_process()
    ideas = load_ideas()
    settled = [a for a in adrs if a["status"] in ("✅", "❌", "🔄")]
    queued = [a for a in adrs if a["status"] in ("⬜", "🟨")]
    far = [a for a in adrs if a["status"] == "⏸"]
    exps = [e for mo in months for e in mo["exps"]]
    open_exps = [e for e in exps if e["status"] in ("⬜", "🟨")]
    done_exps = [e for e in exps if e["status"] in ("✅", "❌")]
    hyps = [h for mo in months for h in mo["hyps"]]
    open_hyps = [h for h in hyps if h["status"] == "⬜"]
    hot = [i for i in ideas if i["status"] == "🟡"]
    L = []
    L.append("# 🎫 上下文卡\n")
    L.append("> 本文件由 compile.py 从三库自动生成，勿手改。作为系统提示词时，从下一行开始全选粘贴。\n")
    L.append("## 我在研究什么\n")
    L.append(_north() + "\n")
    L.append("## 已定的决策（不要动摇我）\n")
    for a in settled:
        L.append(f"- {a['id']} {a['title']}：{a['decision']}" + (f"（依据：{a['basis']}）" if a["basis"] else ""))
    L.append("")
    L.append("## 排队中的实现思路\n")
    for a in queued:
        L.append(f"- {a['id']} {a['title']} {a['status']}：{a['decision']}")
    if far:
        L.append(f"- 远期搁置：" + "；".join(f"{a['id']} {a['title']}" for a in far))
    L.append("")
    L.append("## 实验与假设\n")
    if open_exps:
        L.append("当前实验：")
        for e in open_exps:
            L.append(f"- {e['id']} {e['title']} {e['status']}"
                     + (f"（前置 {e['depends']}）" if e["depends"] else "")
                     + (f"——验证 {e['hypothesis']}" if e["hypothesis"] else ""))
    if open_hyps:
        L.append("未决假设：")
        for h in open_hyps:
            L.append(f"- {h['id']} {h['text']}（{h['exp']}）")
    if done_exps:
        L.append("已有结论：" + "；".join(f"{e['id']} {e['conclusion']}" for e in done_exps if e["conclusion"]))
    L.append("")
    L.append("## 想法池（🟡 候选中）\n")
    for i in hot:
        L.append(f"- {i['id']} {i['title']}" + (f"（归属 {i['owner']}）" if i["owner"] else ""))
    if not hot:
        L.append("-（暂无候选想法）")
    L.append("")
    L.append(f"## 对 AI 的要求\n")
    L.append("延续以上状态讨论，不要重新发明方向。产生值得记录的新想法、决策或实验结果时，提醒我记录"
             "（实时用 MCP 工具 add_idea / add_decision / set_status，或把材料丢进 inbox/ 等同步）。\n")
    return "\n".join(L)


def build_overview():
    adrs, months, ideas = load_adrs(), load_process(), load_ideas()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = [f"# 📊 总览（编译于 {now}）\n"]

    def stat(items):
        c = {}
        for x in items:
            c[x["status"]] = c.get(x["status"], 0) + 1
        return " ｜ ".join(f"{k}×{v}" for k, v in sorted(c.items())) or "空"

    L.append(f"- decisions：{len(adrs)} 条（{stat(adrs)}）")
    L.append(f"- ideas：{len(ideas)} 张（{stat(ideas)}）")
    allexps = [e for mo in months for e in mo["exps"]]
    allhyps = [h for mo in months for h in mo["hyps"]]
    allreads = [r for mo in months for r in mo["reads"]]
    L.append(f"- experiments：{len(allexps)} 个（{stat(allexps)}）｜ 假设 {len(allhyps)} 条 ｜ 阅读 {len(allreads)} 篇\n")
    L.append("## 决策与思路（decisions/）\n")
    L.append("| ID | 标题 | 状态 | 日期 |")
    L.append("|---|---|---|---|")
    for a in adrs:
        L.append(f"| {a['id']} | {a['title']} | {a['status']} | {a['date']} |")
    L.append("")
    L.append("## 想法（ideas/）\n")
    L.append("| ID | 标题 | 状态 | 归属 |")
    L.append("|---|---|---|---|")
    for i in ideas:
        L.append(f"| {i['id']} | {i['title']} | {i['status']} | {i['owner']} |")
    L.append("")
    L.append("## 实验与假设（process/）\n")
    L.append("| ID | 标题/假设 | 状态 | 结论 |")
    L.append("|---|---|---|---|")
    for mo in months:
        for e in mo["exps"]:
            L.append(f"| {e['id']} | {e['title']} | {e['status']} | {e['conclusion']} |")
        for h in mo["hyps"]:
            L.append(f"| {h['id']} | {h['text']} | {h['status']} | {h['exp']} |")
    L.append("")
    L.append("## 阅读（process/）\n")
    L.append("| ID | 材料 | 状态 | 收获 |")
    L.append("|---|---|---|---|")
    for mo in months:
        for r in mo["reads"]:
            L.append(f"| {r['id']} | {r['material']} | {r['status']} | {r['note']} |")
    return "\n".join(L)


def run():
    store.CARD.write_text(build_card() + "\n", encoding="utf-8")
    store.OVERVIEW.write_text(build_overview() + "\n", encoding="utf-8")
    return f"已编译 {store.CARD.name} + {store.OVERVIEW.name}"


if __name__ == "__main__":
    print(run())
