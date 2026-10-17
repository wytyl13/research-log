"""sync.py — 后台同步：新材料 → claude -p（Haiku，便宜模型）提炼 → 写三库 → 编译。

用法：
  python sync.py             手动跑一次完整同步
  python sync.py --detached  自分离后台运行（会话启动钩子用这个）

防递归：claude -p 的 cwd 设在临时目录，其会话 jsonl 不会落进本项目目录。
失败策略：提炼失败则不挪档、不记 seen，材料留待下次。
"""
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import store

PROJ = Path(r"C:\Users\weiyutao\.claude\projects\c--Users-weiyutao-20260823-continual-learning")
INBOX = store.BASE / "inbox"
MAX_FILES = 6          # 每次最多处理的材料数，剩下的留给下次
CHAR_LIMIT = 40000     # 单个材料的截断长度

PROMPT_HEAD = """你是科研记录提炼器。下面给你我的三库索引和一些原始材料（聊天导出/笔记/会话记录）。
任务：从材料中提炼出值得长期保留的条目，输出**一个 JSON 对象**，格式：
{"items": [
 {"type":"idea","title":"...","body":"一两句展开","status":"🟡","owner":"adr-005","links":[]},
 {"type":"decision","title":"...","background":"...","decision":"...","consequence":"...","status":"✅","basis":"..."},
 {"type":"experiment","eid":"E7","title":"...","hypothesis":"...","plan":"...","depends":"E2"},
 {"type":"hypothesis","hid":"H7","text":"可证伪的一句话","experiment":"E7"},
 {"type":"experiment_result","eid":"E2","result":"数字/现象","conclusion":"H1 ✅/❌ + 一句话"},
 {"type":"reading","rid":"R7","material":"...","serves":"服务谁","note":"一句话收获"},
 {"type":"status","target":"adr-005","status":"❌","note":"一句原因"},
 {"type":"status","target":"H1","status":"✅","note":"..."},
 {"type":"status","target":"idea-3","status":"❌","note":"..."},
 {"type":"weekly","week":"2026-W43","lines":["完成: ...","卡点: ...","下周唯一目标: ..."]}
]}
规则：
1. 只输出 JSON，不要任何其他文字。
2. 索引里已存在的条目绝对不要重复添加；材料只是讨论了已有条目且无新信息时，不要产生任何 item。
3. status 可选：⬜ 未开始 🟨 进行中 🟡 感觉可行 ✅ 成立/完成 ❌ 否决 ⏸ 搁置 🔄 被取代。
4. 拿不准归类的，宁可做成 idea，不要丢弃。
5. weekly 仅在材料覆盖了新的一周进展时产生。
"""


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def detached():
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([sys.executable, str(Path(__file__).resolve())], creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)


def load_state():
    if store.STATE.exists():
        return json.loads(store.STATE.read_text(encoding="utf-8"))
    return {"seen": [], "last_run": "1970-01-01T00:00:00"}


def save_state(state):
    store.STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def gather(state):
    mats = []
    for f in sorted(INBOX.glob("*")):
        if f.is_file() and not f.name.startswith(".") and f.suffix != ".part":
            mats.append(("inbox:" + f.name, f))
    for f in sorted(PROJ.glob("*.jsonl"), key=lambda p: p.stat().st_mtime):
        if f.name not in state["seen"]:
            mats.append(("session:" + f.name, f))
    return mats[:MAX_FILES]


def build_index():
    import compile as C
    parts = ["decisions: " + "; ".join(f"{a['id']} {a['title']} {a['status']}" for a in C.load_adrs())]
    for mo in C.load_process():
        parts.append(f"[{mo['month']}] exps: " + "; ".join(f"{e['id']} {e['title']} {e['status']}" for e in mo["exps"]))
        parts.append(f"[{mo['month']}] hyps: " + "; ".join(f"{h['id']} {h['status']}" for h in mo["hyps"]))
        parts.append(f"[{mo['month']}] reads: " + "; ".join(f"{r['id']} {r['status']}" for r in mo["reads"]))
    parts.append("ideas: " + "; ".join(f"{i['id']} {i['title']} {i['status']}" for i in C.load_ideas()))
    return "\n".join(parts)


def build_prompt(mats):
    parts = [PROMPT_HEAD, "## 现有三库索引（已存在，勿重复）\n" + build_index(), "\n## 待提炼材料\n"]
    for label, f in mats:
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")[:CHAR_LIMIT]
        except OSError:
            continue
        parts.append(f"### 材料 {label}\n```\n{txt}\n```\n")
    return "\n".join(parts)


def run_claude(prompt):
    exe = shutil.which("claude") or shutil.which("claude.cmd") or shutil.which("claude.exe")
    if not exe:
        return None, "找不到 claude 命令"
    try:
        r = subprocess.run([exe, "-p", "--model", "haiku"], input=prompt,
                           cwd=tempfile.mkdtemp(), capture_output=True, text=True,
                           encoding="utf-8", errors="ignore", timeout=300)
    except subprocess.TimeoutExpired:
        return None, "claude -p 超时"
    if r.returncode != 0:
        return None, f"claude -p 失败: {r.stderr[:200]}"
    return r.stdout, None


def parse_json(out):
    s, e = out.find("{"), out.rfind("}")
    if s < 0 or e <= s:
        return None
    try:
        return json.loads(out[s:e + 1]).get("items", [])
    except json.JSONDecodeError:
        return None


def apply_items(items):
    report = []
    for it in items:
        t = it.get("type", "")
        try:
            if t == "idea":
                report.append(store.add_idea(it["title"], it.get("body", ""), it.get("status", "🟡"),
                                              it.get("owner", ""), it.get("links")))
            elif t == "decision":
                report.append(store.add_decision(it["title"], it.get("background", ""), it.get("decision", ""),
                                                 it.get("consequence", ""), it.get("status", "✅"), it.get("basis", "")))
            elif t == "experiment":
                report.append(store.add_experiment(it.get("eid") or store.next_exp_id(), it["title"],
                                                   it.get("hypothesis", ""), it.get("plan", ""), "⬜", it.get("depends", "")))
            elif t == "hypothesis":
                report.append(store.add_hypothesis(it.get("hid") or store.next_hyp_id(), it["text"], it.get("experiment", "")))
            elif t == "experiment_result":
                report.append(store.fill_result(it["eid"], it.get("result", ""), it.get("conclusion", "")))
            elif t == "reading":
                report.append(store.add_reading(it.get("rid") or store.next_read_id(), it["material"],
                                                it.get("serves", ""), it.get("note", "")))
            elif t == "status":
                report.append(store.set_status(it["target"], it["status"], it.get("note", "")))
            elif t == "weekly":
                report.append(store.add_weekly(it["week"], it.get("lines", [])))
            else:
                report.append(f"跳过未知类型 {t}")
        except Exception as ex:  # 单条失败不影响其余
            report.append(f"跳过 {t}: {ex}")
    return report


def main():
    state = load_state()
    mats = gather(state)
    if not mats:
        state["last_run"] = now_iso()
        save_state(state)
        print("没有新材料")
        return
    print(f"待处理 {len(mats)} 份材料，开始提炼…")
    out, err = run_claude(build_prompt(mats))
    if out is None:
        print(f"提炼失败：{err}（材料保留，下次再试）")
        return
    items = parse_json(out)
    if items is None:
        print(f"无法解析输出（材料保留）：{out[:200]}")
        return
    rep = apply_items(items)
    done = INBOX / "已处理"
    done.mkdir(exist_ok=True)
    for label, f in mats:
        if label.startswith("inbox:"):
            f.rename(done / f"{datetime.date.today():%Y-%m-%d}-{f.name}")
        else:
            state["seen"].append(f.name)
    state["last_run"] = now_iso()
    save_state(state)
    import compile as C
    C.run()
    print("\n".join(rep) if rep else "材料里没有值得提炼的内容")


if __name__ == "__main__":
    if "--detached" in sys.argv:
        detached()
        print("后台同步已启动")
    else:
        main()
