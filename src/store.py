"""store.py — 三库唯一写入口。

只提供四种合法动作：新建文件、追加条目、改状态行、回填结果/结论。
编号即身份：ADR 四位序号，E/H/R 全局递增，卡片十二位时间戳。
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 源码在 src/，库根是它的上一级

DIRS = ("decisions", "logbook", "ideas", "inbox", "processed")

STATUS = {
    "A": ("建议中", "已采纳", "已被取代", "已废弃"),
    "E": ("未开始", "进行中", "已完成", "搁置"),
    "H": ("待验证", "验证中", "成立", "不成立", "搁置"),
    "R": ("未读", "在读", "已读"),
}

ENTRY_FIELDS = {  # 条目字段固定，聚合按行抓取
    "E": ("状态", "假设", "方案", "前置", "结果", "结论"),
    "H": ("状态", "验证实验"),
    "R": ("状态", "服务", "收获"),
}

_HEAD_RE = re.compile(r"^## ([EHR])(\d+) · ", re.M)
_LINK_RE = re.compile(r"\[\[\s*([^\]\s]+)\s*\]\]")


def set_root(path) -> None:
    """自测用：把库根指到别处。"""
    global ROOT
    ROOT = Path(path)


def init() -> None:
    for d in DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)


def _check_status(kind: str, status: str) -> None:
    if status not in STATUS[kind]:
        raise ValueError(f"非法状态「{status}」，只能用：{' / '.join(STATUS[kind])}")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _append(path: Path, text: str) -> None:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    _write(path, (old.rstrip("\n") + "\n\n" + text) if old else text)


# ponytail: 编号靠全库扫描取最大号，库到千条量级再考虑缓存
def _next(kind: str) -> int:
    if kind == "A":
        nums = [int(p.stem) for p in (ROOT / "decisions").glob("*.md") if p.stem.isdigit()]
        return max(nums) + 1 if nums else 1
    best = 0
    for p in (ROOT / "logbook").glob("*.md"):
        for k, n in _HEAD_RE.findall(p.read_text(encoding="utf-8")):
            if k == kind:
                best = max(best, int(n))
    return best + 1


def _norm(ref: str) -> tuple[str, int] | tuple[str, str]:
    """编号归一：('A', 序号) / ('E'|'H'|'R', 序号) / ('T', 时间戳)。"""
    s = ref.strip().upper().replace("ADR-", "")
    if re.fullmatch(r"\d{12}", s):
        return ("T", s)
    if re.fullmatch(r"[EHR]\d+", s):
        return (s[0], int(s[1:]))
    if re.fullmatch(r"\d{1,4}", s):
        return ("A", int(s))
    raise KeyError(f"认不出编号：{ref}")


def resolve(ref: str) -> tuple[Path, int]:
    """编号 → (文件, 标题行号)。"""
    kind, val = _norm(ref)
    if kind == "A":
        p = ROOT / "decisions" / f"{val:04d}.md"
        if not p.exists():
            raise KeyError(f"没有这个决策：{ref}")
        return p, 1
    if kind == "T":
        p = ROOT / "ideas" / f"{val}.md"
        if not p.exists():
            raise KeyError(f"没有这张卡片：{ref}")
        return p, 1
    pat = re.compile(rf"^## {kind}{val} · ", re.M)
    for p in sorted((ROOT / "logbook").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = pat.search(text)
        if m:
            return p, text[: m.start()].count("\n") + 1
    raise KeyError(f"没有这个条目：{ref}")


def get(ref: str) -> str:
    p, _ = resolve(ref)
    return p.read_text(encoding="utf-8")


def add_decision(title, status="建议中", context="", decision="", consequence="", basis="") -> str:
    _check_status("A", status)
    n = _next("A")
    text = (
        f"# {n}. {title}\n\n"
        f"日期: {datetime.now():%Y-%m-%d}\n\n"
        f"## 状态\n\n{status}\n\n"
        f"## 背景\n\n{context}\n\n"
        f"## 决定\n\n{decision}\n\n"
        f"## 后果\n\n{consequence}\n\n"
        f"## 依据\n\n{basis}\n"
    )
    _write(ROOT / "decisions" / f"{n:04d}.md", text)
    return f"{n:04d}"


def _entry(kind: str, n: int, title: str, values: dict) -> str:
    lines = [f"## {kind}{n} · {title}", ""]
    lines += [f"- {f}: {values.get(f, '')}" for f in ENTRY_FIELDS[kind]]
    return "\n".join(lines) + "\n"


def _add_entry(kind: str, title: str, values: dict) -> str:
    n = _next(kind)
    day = ROOT / "logbook" / f"{datetime.now():%Y-%m-%d}.md"
    if not day.exists():
        _write(day, f"# {datetime.now():%Y-%m-%d} 实验记录本\n")
    _append(day, _entry(kind, n, title, values))
    return f"{kind}{n}"


def add_experiment(title, status="未开始", hypothesis="", plan="", prior="", result="", conclusion="") -> str:
    _check_status("E", status)
    return _add_entry("E", title, {"状态": status, "假设": hypothesis, "方案": plan,
                                   "前置": prior, "结果": result, "结论": conclusion})


def add_hypothesis(title, status="待验证", verify="") -> str:
    _check_status("H", status)
    return _add_entry("H", title, {"状态": status, "验证实验": verify})


def add_reading(title, status="未读", serves="", gain="") -> str:
    _check_status("R", status)
    return _add_entry("R", title, {"状态": status, "服务": serves, "收获": gain})


def add_idea(title, text, links=()) -> str:
    stamp = datetime.now()
    while True:
        name = f"{stamp:%Y%m%d%H%M}"
        if not (ROOT / "ideas" / f"{name}.md").exists():
            break
        stamp += timedelta(minutes=1)  # 同分钟撞名则顺延一分钟
    body = f"# {title}\n\n{text}\n"
    if links:
        body += f"\n链接：{' '.join(f'[[{l}]]' for l in links)}\n"
    _write(ROOT / "ideas" / f"{name}.md", body)
    return name


def set_status(ref: str, new_status: str) -> None:
    kind, _ = _norm(ref)
    _check_status(kind, new_status)
    p, line = resolve(ref)
    lines = p.read_text(encoding="utf-8").split("\n")
    if kind == "A":
        i = lines.index("## 状态")
        j = next(k for k in range(i + 1, len(lines)) if lines[k].strip())
        lines[j] = new_status
    else:
        for k in range(line, len(lines)):  # 只在条目块内找，到下个 ## 为止
            if lines[k].startswith("## "):
                break
            if lines[k].startswith("- 状态:"):
                lines[k] = f"- 状态: {new_status}"
                break
        else:
            raise ValueError(f"{ref} 条目里没有状态行")
    _write(p, "\n".join(lines))


def fill_result(ref: str, result="", conclusion="") -> None:
    if _norm(ref)[0] != "E":
        raise ValueError("只有实验条目能回填结果/结论")
    p, line = resolve(ref)
    lines = p.read_text(encoding="utf-8").split("\n")
    hit = {"结果": False, "结论": False}
    for k in range(line, len(lines)):  # 条目块内只碰结果/结论两行
        if lines[k].startswith("## "):
            break
        for f, v in (("结果", result), ("结论", conclusion)):
            if v and lines[k].startswith(f"- {f}:"):
                lines[k] = f"- {f}: {v}"
                hit[f] = True
    for f, v in (("结果", result), ("结论", conclusion)):
        if v and not hit[f]:
            raise ValueError(f"{ref} 条目里没有{f}行")
    _write(p, "\n".join(lines))


def scan_links() -> dict[str, list[str]]:
    """反向索引：编号 → 引用它的文件列表。"""
    index: dict[str, list[str]] = {}
    files = sorted((ROOT / "decisions").glob("*.md")) + \
        sorted((ROOT / "logbook").glob("*.md")) + sorted((ROOT / "ideas").glob("*.md"))
    for p in files:
        for m in _LINK_RE.finditer(p.read_text(encoding="utf-8")):
            index.setdefault(m.group(1), []).append(p.relative_to(ROOT).as_posix())
    return index
