"""migrate_v3.py — 一次性迁移：v2 备份 → v3 严格标准三库。

从 _backup_v2/ 读，写到 _new_v3/，绝不碰现场。
用法：C:/ProgramData/anaconda3/python.exe -X utf8 migrate_v3.py
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC = BASE / "_backup_v2"
DST = BASE / "_new_v3"

ADR_ST = {"✅": "已采纳", "⬜": "建议中", "⏸": "建议中"}      # ⏸ 另在背景补"远期暂缓"
EXP_ST = {"⬜": "未开始", "🟨": "进行中", "✅": "已完成", "❌": "搁置"}
HYP_ST = {"⬜": "待验证", "🟨": "验证中", "✅": "成立", "❌": "不成立", "⏸": "搁置"}
READ_ST = {"⬜": "未读", "🟨": "在读", "✅": "已读"}
FOLD = {"⬆️": "（发展：已升级为正式条目，见链接。）", "🟡": "（直觉：可行，待验证。）",
        "⏸": "（定位：远期方向。）", "✅": "（结果：已落地实现。）", "⬜": "（状态：待评估。）"}

rewrites = []      # (原文, 新文)
unresolved = []    # 无法解析的引用


def field(text, name):
    r = re.search(rf"^-\s*{name}\s*:[ \t]*(.*)$", text, re.M)
    return r.group(1).strip() if r else ""


# ---------- 1. ADR ----------

adr_files = sorted((SRC / "decisions").glob("adr-*.md"))
adr_map = {}   # 旧编号 int -> 新 stem
for f in adr_files:
    n = int(re.match(r"adr-(\d+)", f.name).group(1))
    adr_map[n] = f"{n:04d}-{f.name[len(f'adr-{n:03d}-'):-3]}"


def linkify(text):
    """正文纯文本 adr-00N → [[新文件名]]；支持 adr-005/006/007 与 adr-005–007 连写。"""
    def one(num_str):
        new = adr_map.get(int(num_str))
        if new:
            rewrites.append((num_str, new))
            return f"[[{new}]]"
        unresolved.append(num_str)
        return num_str

    def group(m):
        return "/".join(one(x) for x in re.findall(r"\d{3}", m.group(0)))

    text = re.sub(r"adr-\d{3}(?:[/]\d{3})+", group, text)
    text = re.sub(r"(?<!\[)adr-(\d{3})", lambda m: one(m.group(1)), text)
    return re.sub(r"([/–])(\d{3})(?=[^\d-]|$)", lambda m: m.group(1) + one(m.group(2)), text)


new_adrs = []
for f in adr_files:
    t = f.read_text(encoding="utf-8")
    n = int(re.match(r"adr-(\d+)", f.name).group(1))
    title = re.search(r"^#\s+ADR-\d+\s*[:：]\s*(.+)$", t, re.M).group(1).strip()
    st_old = field(t, "状态")
    st = ADR_ST[st_old]
    bg = linkify(field(t, "背景"))
    if st_old == "⏸":
        bg += "（远期暂缓）"
    body = f"""# {n}. {title}

日期: {field(t, '日期')}

## 状态

{st}

## 背景

{bg}

## 决定

{linkify(field(t, '决定'))}

## 后果

{linkify(field(t, '后果'))}

## 依据

{linkify(field(t, '依据'))}
"""
    (DST / "decisions").mkdir(parents=True, exist_ok=True)
    (DST / "decisions" / f"{adr_map[n]}.md").write_text(body, encoding="utf-8")
    new_adrs.append((n, title, st))

# ---------- 2. ideas ----------

idea_files = sorted((SRC / "ideas").glob("[0-9]*-*.md"))
old_ids = [int(re.match(r"(\d+)-", f.name).group(1)) for f in idea_files]
base_ts = datetime.fromtimestamp(idea_files[0].stat().st_mtime).replace(second=0, microsecond=0)
idea_map = {}       # 旧 id int -> 新 stem
idea_by_stem = {}   # 旧文件名 stem -> 新 stem
for i, f in enumerate(idea_files):
    stem = f"{base_ts + timedelta(minutes=i):%Y%m%d%H%M}-{f.name[len(f'{old_ids[i]:03d}-'):-3]}"
    idea_map[old_ids[i]] = stem
    idea_by_stem[f.stem] = stem


def resolve_link(tok):
    inner = tok.strip().strip('"').strip("[]")
    m = re.fullmatch(r"adr-(\d+)", inner)
    if m:
        return adr_map.get(int(m.group(1)))
    m = re.fullmatch(r"idea-(\d+)", inner)
    if m:
        return idea_map.get(int(m.group(1)))
    return idea_by_stem.get(inner)


cards = []
for f in idea_files:
    t = f.read_text(encoding="utf-8")
    fm = t.split("---")[1]
    body = t.split("---", 2)[2].strip()
    old_id = int(re.match(r"(\d+)-", f.name).group(1))

    def fmf(k):
        r = re.search(rf"^{k}\s*:\s*(.*)$", fm, re.M)
        return r.group(1).strip() if r else ""

    links = []
    for tok in [fmf("owner")] + re.findall(r"\[\[(.+?)\]\]", fmf("links")):
        tok = tok.strip().strip('"').strip()
        if not tok:
            continue
        r = resolve_link(tok)
        if r:
            links.append(r)
        else:
            unresolved.append(f"{f.name}: {tok}")
    fold = FOLD.get(fmf("status"), "")
    text = f"{body}\n\n{fold}\n"
    if links:
        seen, uniq = set(), []
        for l in links:
            if l not in seen:
                seen.add(l)
                uniq.append(l)
        text += "\n链接：" + " ".join(f"[[{l}]]" for l in uniq) + "\n"
    (DST / "ideas").mkdir(parents=True, exist_ok=True)
    (DST / "ideas" / f"{idea_map[old_id]}.md").write_text(text, encoding="utf-8")
    cards.append((idea_map[old_id], body.splitlines()[0].lstrip("# ").strip()))

# ---------- 3. process：月表 → 按日条目 ----------

pt = next(iter((SRC / "process").glob("*.md"))).read_text(encoding="utf-8")
day = "2026-10-17"   # 全部条目都是 10-17 创建
hyps = [m.groups() for m in re.finditer(
    r"^\|\s*(H\d+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(\S+)\s*\|", pt, re.M)]
reads = [m.groups() for m in re.finditer(
    r"^\|\s*(R\d+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*(\S+)\s*\|\s*(.*?)\s*\|", pt, re.M)]
exps = []
for m in re.finditer(r"^###\s+\d{4}-\d{2}-\d{2}\s+(E\d+)\s*[:：]\s*(.+?)\s*([⬜🟨🟡✅❌⏸🔄⬆️])?\s*$", pt, re.M):
    eid, title, st = m.group(1), m.group(2).strip(), m.group(3) or "⬜"
    tail = pt[m.end():m.end() + 600]
    exps.append((eid, title, st, {k: field(tail, k) for k in ("假设", "服务", "前置", "方案沿革", "结果", "结论")}))

# 周志：同周两组相近行 → 逐键合并（互含取长者，否则并接）
wk = re.search(r"^###\s+(2026-W\d+).*?(?=^## |\Z)", pt, re.S | re.M)
week_id = wk.group(1)
pairs = {}
for k, v in re.findall(r"^- (\S+?): (.*)$", wk.group(0), re.M):
    v = v.strip()
    if k not in pairs:
        pairs[k] = v
    elif v in pairs[k] or pairs[k] in v:
        pairs[k] = max(pairs[k], v, key=len)
    else:
        pairs[k] += f"；{v}"

L = [f"# {day} 实验记录本"]
for eid, title, st, fl in sorted(exps):
    L.append(f"\n## {eid} · {title}")
    L.append(f"- 状态: {EXP_ST[st]}")
    for old, new in (("假设", "假设"), ("服务", "服务"), ("前置", "前置"), ("方案沿革", "方案"), ("结果", "结果"), ("结论", "结论")):
        if fl[old]:
            L.append(f"- {new}: {linkify(fl[old])}")
for hid, text, ve, st in sorted(hyps):
    L.append(f"\n## {hid} · {text}")
    L.append(f"- 状态: {HYP_ST[st]}")
    L.append(f"- 验证实验: {linkify(ve)}")
for rid, material, serves, st, note in sorted(reads):
    L.append(f"\n## {rid} · {material}")
    L.append(f"- 状态: {READ_ST[st]}")
    L.append(f"- 服务: {linkify(serves)}")
    if note:
        L.append(f"- 收获: {linkify(note)}")
L.append(f"\n## W42 · 周记")
for k, v in pairs.items():
    L.append(f"- {k}: {v}")
(DST / "process").mkdir(parents=True, exist_ok=True)
(DST / "process" / f"{day}.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# ---------- 4. 方向.md → 结构笔记 ----------

north = (SRC / "方向.md").read_text(encoding="utf-8").strip()
north += "\n\n## 链接\n\n"
north += "- 决策主线：[[" + adr_map[1] + "]]\n"
north += "- 验证路径：[[" + adr_map[2] + "]]\n"
north += "- 排队思路：[[" + adr_map[5] + "]]、[[" + adr_map[6] + "]]、[[" + adr_map[7] + "]]\n"
north += "- 远期：[[" + adr_map[8] + "]]\n"
(DST / "方向.md").write_text(north, encoding="utf-8")

# ---------- 5. 对照表 + 报告 ----------

cmp_ = ["# v2 → v3 文件名对照\n", "| 旧 | 新 |", "|---|---|"]
for n in sorted(adr_map):
    cmp_.append(f"| adr-{n:03d} | {adr_map[n]} |")
for i in sorted(idea_map):
    cmp_.append(f"| {idea_files[old_ids.index(i)].name} | {idea_map[i]}.md |")
(DST / "文件名对照.md").write_text("\n".join(cmp_) + "\n", encoding="utf-8")

print("== 迁移报告 ==")
print(f"ADR：{len(new_adrs)} 条 → " + "；".join(f"{n:04d} {st}" for n, _, st in new_adrs))
print(f"卡片：{len(cards)} 张（基准时间 {base_ts:%H:%M} 起，分钟递增）")
for stem, title in cards:
    print(f"  {stem} {title}")
print(f"过程：实验 {len(exps)} 条（{', '.join(sorted(e[0] for e in exps))}）、假设 {len(hyps)} 条、"
      f"阅读 {len(reads)} 条、周记 1 条（{week_id} 合并为 {len(pairs)} 行）")
print(f"纯文本 adr-00N 改写：{len(rewrites)} 处")
if unresolved:
    print("!! 未识别引用（需人工处理）：")
    for u in unresolved:
        print("   ", u)
else:
    print("未识别引用：无")
print("W42 合并结果：")
for k, v in pairs.items():
    print(f"  {k}: {v[:80]}")
