"""store.py — 科研记录三库（decisions/process/ideas）的读写原语。

被 research-mcp/server.py（实时单条）和 sync.py（批量提炼）共用。
铁律：只增不删——本模块没有任何删除操作；变更只允许新建文件、追加条目、改状态。
所有路径通过 store.X 属性访问（selftest 时可整体替换到临时目录）。
"""
import datetime
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
D_DIR = BASE / "decisions"    # ADR 模式：决策 + 实现思路
P_DIR = BASE / "process"      # 实验记录本模式：假设/实验/阅读/周志，按月一文件
I_DIR = BASE / "ideas"        # 卡片盒模式：原子想法，Obsidian 兼容
STATE = BASE / ".记录状态.json"
CARD = BASE / "上下文卡.md"
OVERVIEW = BASE / "总览.md"
NORTH = BASE / "方向.md"

STATUSES = ("⬜", "🟨", "🟡", "✅", "❌", "⏸", "🔄", "⬆️")


def today():
    return datetime.date.today().isoformat()


def slug(title, limit=24):
    s = re.sub(r"[^\w一-鿿]+", "-", str(title)).strip("-")
    return s[:limit] or "untitled"


def _swap_icon(line, status):
    for s in STATUSES:
        if s in line:
            return line.replace(s, status, 1)
    return None


def _table_extent(lines, marker):
    """marker 所在节内第一个 markdown 表格的行号范围（遇到下一个标题即止）。"""
    try:
        start = next(i for i, l in enumerate(lines) if marker in l)
    except StopIteration:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("#"):
            end = i
            break
    rows = [i for i in range(start, end)
            if lines[i].lstrip().startswith("|") and re.search(r"[^\s|:-]", lines[i])]
    return (rows[0], rows[-1]) if rows else None


# ---------- decisions（ADR）----------

def next_adr_id():
    return max((int(m.group(1)) for f in D_DIR.glob("adr-*.md")
                if (m := re.match(r"adr-(\d+)", f.name))), default=0) + 1


def add_decision(title, background="", decision="", consequence="", status="✅", basis=""):
    D_DIR.mkdir(exist_ok=True)
    n = next_adr_id()
    f = D_DIR / f"adr-{n:03d}-{slug(title)}.md"
    f.write_text(f"""# ADR-{n:03d}: {title}

- 日期: {today()}
- 状态: {status}
- 背景: {background}
- 决定: {decision}
- 后果: {consequence}
- 依据: {basis}
""", encoding="utf-8")
    return f"ADR-{n:03d} 已记录：{title}"


# ---------- ideas（卡片盒）----------

def next_idea_id():
    return max((int(m.group(1)) for f in I_DIR.glob("*.md")
                if (m := re.match(r"(\d+)-", f.name))), default=0) + 1


def add_idea(title, body="", status="🟡", owner="", links=None):
    I_DIR.mkdir(exist_ok=True)
    n = next_idea_id()
    owner_s = f"\"[[{owner}]]\"" if owner else '""'
    links_s = ", ".join(f"\"[[{x}]]\"" for x in (links or []))
    f = I_DIR / f"{n:03d}-{slug(title)}.md"
    f.write_text(f"""---
id: {n}
date: {today()}
status: {status}
owner: {owner_s}
links: [{links_s}]
---

# {title}

{body}
""", encoding="utf-8")
    return f"想法 #{n:03d} 已记录：{title}"


# ---------- process（实验记录本，按月一文件）----------

def _ensure_month():
    P_DIR.mkdir(exist_ok=True)
    f = P_DIR / f"{datetime.date.today():%Y-%m}.md"
    if not f.exists():
        f.write_text(f"""# {datetime.date.today():%Y-%m} 实验记录

## 假设登记

| ID | 假设 | 验证实验 | 状态 |
|---|---|---|---|

## 阅读

| ID | 材料 | 服务 | 状态 | 一句话收获 |
|---|---|---|---|---|

## 周志

## 实验
""", encoding="utf-8")
    return f


def _scan_month_ids(row_pat):
    n = 0
    for f in P_DIR.glob("*.md"):
        for m in re.finditer(row_pat, f.read_text(encoding="utf-8")):
            n = max(n, int(m.group(1)))
    return n


def next_exp_id():
    return f"E{_scan_month_ids(r'###\s+\d{4}-\d{2}-\d{2}\s+E(\d+)\s*:') + 1}"


def next_hyp_id():
    return f"H{_scan_month_ids(r'\|\s*H(\d+)\s*\|') + 1}"


def next_read_id():
    return f"R{_scan_month_ids(r'\|\s*R(\d+)\s*\|') + 1}"


def add_experiment(eid, title, hypothesis="", plan="", status="⬜", depends=""):
    f = _ensure_month()
    block = f"\n### {today()} {eid}: {title} {status}\n"
    if hypothesis:
        block += f"- 假设: {hypothesis}\n"
    if depends:
        block += f"- 前置: {depends}\n"
    if plan:
        block += f"- 方案沿革: v1（{today()[5:]}）{plan}\n"
    block += "- 结果: \n- 结论: \n"
    with f.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return f"{eid} 已登记：{title}"


def add_hypothesis(hid, text, experiment="", status="⬜"):
    f = _ensure_month()
    lines = f.read_text(encoding="utf-8").splitlines()
    ext = _table_extent(lines, "## 假设登记")
    if not ext:
        return "错误：月文件里找不到假设表"
    lines.insert(ext[1] + 1, f"| {hid} | {text} | {experiment} | {status} |")
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"{hid} 已登记"


def add_reading(rid, material, serves="", note="", status="⬜"):
    f = _ensure_month()
    lines = f.read_text(encoding="utf-8").splitlines()
    ext = _table_extent(lines, "## 阅读")
    if not ext:
        return "错误：月文件里找不到阅读表"
    lines.insert(ext[1] + 1, f"| {rid} | {material} | {serves} | {status} | {note} |")
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"{rid} 已登记"


def add_weekly(week, lines_to_add):
    f = _ensure_month()
    lines = f.read_text(encoding="utf-8").splitlines()
    for i, l in enumerate(lines):
        if l.strip() == f"### {week}":
            for j, item in enumerate(lines_to_add):
                lines.insert(i + 1 + j, f"- {item}")
            f.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return f"{week} 已追加 {len(lines_to_add)} 行"
    try:
        anchor = next(i for i, l in enumerate(lines) if l.strip() == "## 实验")
    except StopIteration:
        lines.append(f"\n### {week}")
        lines.extend(f"- {x}" for x in lines_to_add)
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"{week} 已新建"
    new = [f"### {week}"] + [f"- {x}" for x in lines_to_add] + [""]
    lines[anchor:anchor] = new
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"{week} 已新建"


def fill_result(eid, result="", conclusion=""):
    for f in sorted(P_DIR.glob("*.md"), reverse=True):
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, l in enumerate(lines):
            if re.search(rf"### .*\b{re.escape(eid)}\b\s*:", l):
                for j in range(i, min(i + 15, len(lines))):
                    if result and lines[j].startswith("- 结果"):
                        lines[j] = f"- 结果: {result}"
                    if conclusion and lines[j].startswith("- 结论"):
                        lines[j] = f"- 结论: {conclusion}"
                f.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return f"{eid} 已回填结果/结论"
    return f"未找到实验 {eid}"


# ---------- 状态变更 ----------

def _replace_kv_status(path, status, note, label):
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, l in enumerate(lines):
        if re.match(r"(-\s*状态|status)\s*:\s*\S", l):
            new = _swap_icon(l, status)
            if new is None:
                return f"{label} 有状态行但没有可替换的图标"
            lines[i] = new
            if note:
                lines.append(f"- 备注({today()}): {note}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return f"{label} 状态改为 {status}"
    return f"{label} 里没有状态行"


def set_status(target, status, note=""):
    if status not in STATUSES:
        return "非法状态：" + status
    t = target.strip().lower().replace("：", ":")
    if (m := re.fullmatch(r"adr[- :]?(\d+)", t)):
        files = list(D_DIR.glob(f"adr-{int(m.group(1)):03d}-*.md"))
        return _replace_kv_status(files[0], status, note, f"ADR-{int(m.group(1)):03d}") if files else f"未找到 ADR-{m.group(1)}"
    if (m := re.fullmatch(r"idea[- :]?(\d+)", t)):
        files = list(I_DIR.glob(f"{int(m.group(1)):03d}-*.md"))
        return _replace_kv_status(files[0], status, note, f"idea-{m.group(1)}") if files else f"未找到 idea-{m.group(1)}"
    # H/E/R 在 process 月文件里
    tgt = target.strip()
    for f in sorted(P_DIR.glob("*.md"), reverse=True):
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, l in enumerate(lines):
            if re.match(rf"\|\s*{re.escape(tgt)}\s*\|", l) or re.search(rf"### .*\b{re.escape(tgt)}\b\s*:", l):
                new = _swap_icon(l, status)
                if new is None:
                    continue
                if note and new.rstrip().endswith("|"):
                    new = new.rstrip()[:-1].rstrip() + f" {note} |"
                elif note:
                    new += f"  # {note}"
                lines[i] = new
                f.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return f"{tgt} 状态改为 {status}"
    return f"未找到 {target}"
