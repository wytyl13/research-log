"""store.py — 三库读写原语（v3：严格 ADR / 实验记录本 / Zettelkasten）。

被 research-mcp/server.py（实时单条）和 sync.py（批量提炼）共用。
铁律：只增不删——只允许新建文件、追加条目、改状态、回填结果。

规范：
  decisions/  NNNN-标题.md          节式 ADR（状态/背景/决定/后果/依据），状态用文字
  process/    YYYY-MM-DD.md         按日一文件；条目 = "## E2 · 标题" + "- 字段: 值" 行
  ideas/      YYYYMMDDHHMM-标题.md  原子卡片，无状态无归属，靠 [[链接]] 长出结构

所有路径通过模块属性访问（selftest 可整体换到临时目录）。
"""
import datetime
import os
import re
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
D_DIR = BASE / "decisions"
P_DIR = BASE / "process"
I_DIR = BASE / "ideas"
STATE = BASE / ".记录状态.json"
CARD = BASE / "上下文卡.md"
OVERVIEW = BASE / "总览.md"
NORTH = BASE / "方向.md"
LOCK = BASE / ".写入锁"

# ---- 状态枚举（store / compile / sync 四方共用的契约）----
ADR_STATUSES = ("建议中", "已采纳", "已被取代", "已废弃")   # 「已被取代」可带（ADR-NNNN）
HYP_STATUSES = ("待验证", "验证中", "成立", "不成立", "搁置")
EXP_STATUSES = ("未开始", "进行中", "已完成", "搁置")
READ_STATUSES = ("未读", "在读", "已读")

ENTRY_HEAD = re.compile(r"^## ([EHRW]\d+) · (.+)$", re.M)
FIELD_LINE = re.compile(r"^- ([^:：]+):[ \t]*(.*)$", re.M)


def today():
    return datetime.date.today().isoformat()


def slug(title, limit=24):
    s = re.sub(r"[^\w一-鿿]+", "-", str(title)).strip("-")
    return s[:limit] or "untitled"


class _Lock:
    """跨进程写入锁：O_CREAT|O_EXCL 自旋；持有者崩溃超过 120 秒自动清死锁。"""

    def __enter__(self):
        deadline = time.time() + 60
        while True:
            try:
                self.fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                try:
                    if time.time() - LOCK.stat().st_mtime > 120:
                        LOCK.unlink()
                        continue
                except OSError:
                    pass
                if time.time() > deadline:
                    raise TimeoutError("写入锁等待超时")
                time.sleep(0.1)

    def __exit__(self, *a):
        os.close(self.fd)
        try:
            LOCK.unlink()
        except OSError:
            pass


# ---------- decisions（严格 ADR）----------

def _adr_titles():
    """{编号: 标题}，解析失败的不计。"""
    out = {}
    for f in sorted(D_DIR.glob("????-*.md")):
        m = re.search(r"^# (\d+)\. (.+)$", f.read_text(encoding="utf-8"), re.M)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def add_adr(title, background="", decision="", consequence="", basis="", status="已采纳"):
    if status not in ADR_STATUSES and not status.startswith("已被取代"):
        return f"非法状态：{status}（允许：{'/'.join(ADR_STATUSES)}）"
    with _Lock():
        D_DIR.mkdir(exist_ok=True)
        titles = _adr_titles()
        for n, t in titles.items():
            if t == title:
                return f"已存在同题 ADR-{n:04d}，跳过：{title}"
        n = max(titles, default=0) + 1
        f = D_DIR / f"{n:04d}-{slug(title)}.md"
        f.write_text(f"""# {n}. {title}

日期: {today()}

## 状态

{status}

## 背景

{background}

## 决定

{decision}

## 后果

{consequence}

## 依据

{basis}
""", encoding="utf-8")
    return f"ADR-{n:04d} 已记录：{title}"


# ---------- ideas（严格 Zettelkasten）----------

def add_card(title, body="", links=None):
    with _Lock():
        I_DIR.mkdir(exist_ok=True)
        for f in sorted(I_DIR.glob("*.md")):
            m = re.search(r"^# (.+)$", f.read_text(encoding="utf-8"), re.M)
            if m and m.group(1).strip() == title:
                return f"已存在同题卡片 {f.stem}，跳过：{title}"
        ts = datetime.datetime.now()
        while True:
            stem = f"{ts:%Y%m%d%H%M}-{slug(title, 30)}"
            if not (I_DIR / (stem + ".md")).exists():
                break
            ts += datetime.timedelta(minutes=1)   # 同分钟撞号则递增
        text = f"# {title}\n\n{body}\n"
        links = [l for l in (links or []) if l]
        if links:
            text += "\n链接：" + " ".join(f"[[{l}]]" for l in links) + "\n"
        (I_DIR / (stem + ".md")).write_text(text, encoding="utf-8")
    return f"卡片 {stem} 已记录：{title}"


# ---------- process（严格实验记录本：按日一文件，条目追加）----------

def _entries():
    """全部条目 [{day, id, title, fields}]，按日文件名排序。"""
    out = []
    for f in sorted(P_DIR.glob("????-??-??.md")):
        t = f.read_text(encoding="utf-8")
        heads = list(ENTRY_HEAD.finditer(t))
        for i, m in enumerate(heads):
            block = t[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(t)]
            out.append(dict(day=f.stem, id=m.group(1), title=m.group(2).strip(),
                            fields={k.strip(): v.strip() for k, v in FIELD_LINE.findall(block)}))
    return out


def _next_entry_num(letter):
    return max((int(e["id"][1:]) for e in _entries() if e["id"][0] == letter), default=0) + 1


def _entry_statuses(letter):
    return {"E": EXP_STATUSES, "H": HYP_STATUSES, "R": READ_STATUSES}[letter]


def add_entry(letter, title, fields):
    """往今天的日文件追加一条条目。letter ∈ E/H/R/W；E/H/R 必须带合法「状态」。"""
    letter = letter.upper()
    if letter not in "EHRW":
        return f"非法条目类型：{letter}"
    fields = {k: str(v).strip() for k, v in fields.items() if str(v).strip()}
    if letter in "EHR":
        st = fields.get("状态") or {"E": "未开始", "H": "待验证", "R": "未读"}[letter]
        if st not in _entry_statuses(letter):
            return f"非法状态：{st}（{letter} 允许：{'/'.join(_entry_statuses(letter))}）"
        fields = {"状态": st, **fields}
    with _Lock():
        P_DIR.mkdir(exist_ok=True)
        eid = f"{letter}{_next_entry_num(letter)}"
        day = P_DIR / f"{datetime.date.today():%Y-%m-%d}.md"
        if not day.exists():
            day.write_text(f"# {day.stem} 实验记录本\n", encoding="utf-8")
        with day.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {eid} · {title}\n")
            for k, v in fields.items():
                fh.write(f"- {k}: {v}\n")
    return f"{eid} 已登记：{title}"


def _find_entry(eid):
    """返回 (日文件, 全文, 条目起始行号, 条目结束行号)；找不到返回 None。"""
    for f in sorted(P_DIR.glob("????-??-??.md"), reverse=True):
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, l in enumerate(lines):
            if l.startswith(f"## {eid} ·"):
                end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
                return f, lines, i, end
    return None


def set_status(target, status, note=""):
    """改状态。目标：adr-005 / 0005 / E2 / H1 / R1。想法卡片没有状态。"""
    t = str(target).strip().lower().replace("：", ":")
    if (m := re.fullmatch(r"adr[- :]?0*(\d+)", t)):
        n = int(m.group(1))
        if status not in ADR_STATUSES and not status.startswith("已被取代"):
            return f"非法状态：{status}（允许：{'/'.join(ADR_STATUSES)}）"
        files = list(D_DIR.glob(f"{n:04d}-*.md"))
        if not files:
            return f"未找到 ADR-{n:04d}"
        with _Lock():
            f = files[0]
            text = f.read_text(encoding="utf-8")
            new = re.sub(r"(## 状态\s*\n+)[^\n]+", rf"\g<1>{status}", text, count=1)
            if new == text and "## 状态" not in text:
                return f"ADR-{n:04d} 文件里没有状态节"
            if note:
                new += f"\n> {today()} 备注: {note}\n"
            f.write_text(new, encoding="utf-8")
        return f"ADR-{n:04d} 状态改为 {status}"
    if (m := re.fullmatch(r"([ehrw])[- :]?0*(\d+)", t)):
        eid = f"{m.group(1).upper()}{m.group(2)}"
        letter = eid[0]
        if letter == "W":
            return "周记条目没有状态"
        allowed = _entry_statuses(letter)
        if status not in allowed:
            return f"非法状态：{status}（{eid} 允许：{'/'.join(allowed)}）"
        found = _find_entry(eid)
        if not found:
            return f"未找到 {eid}"
        f, lines, start, end = found
        with _Lock():
            note_s = f"（{today()}：{note}）" if note else ""
            for i in range(start + 1, end):
                if lines[i].startswith("- 状态:"):
                    lines[i] = f"- 状态: {status}{note_s}"
                    break
            else:
                lines.insert(start + 1, f"- 状态: {status}{note_s}")
            f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"{eid} 状态改为 {status}"
    return f"无法识别目标：{target}（想法卡片没有状态）"


def fill_result(eid, result="", conclusion=""):
    """回填实验的结果/结论；已有内容则追加（旧；新）。"""
    eid = str(eid).strip().upper()
    found = _find_entry(eid)
    if not found:
        return f"未找到实验 {eid}"
    f, lines, start, end = found
    with _Lock():
        for key, val in (("结果", result), ("结论", conclusion)):
            if not str(val).strip():
                continue
            for i in range(start + 1, end):
                if lines[i].startswith(f"- {key}:"):
                    old = lines[i][len(f"- {key}:"):].strip()
                    lines[i] = f"- {key}: " + (f"{old}；{val}" if old else val)
                    break
            else:
                lines.insert(end, f"- {key}: {val}")
                end += 1
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"{eid} 已回填结果/结论"


def resolve(ref):
    """把 adr-005 / 5 / 0005 / 卡片文件名（或其片段）解析成实际文件 stem；失败原样返回。"""
    ref = str(ref).strip()
    if (m := re.fullmatch(r"(?:adr[- ]?)?0*(\d+)", ref, re.I)):
        hits = [f.stem for f in D_DIR.glob(f"{int(m.group(1)):04d}-*.md")]
        if hits:
            return hits[0]
    hits = [f.stem for f in I_DIR.glob(f"*{ref}*.md")]
    return hits[0] if len(hits) == 1 else ref
