"""research-log MCP server（三库版 v3：严格 ADR / 实验记录本 / Zettelkasten）

让任何支持 MCP 的 AI 客户端（Cherry Studio / Claude Desktop / Claude Code）直接读写
科研记录三库。stdio 传输，无状态。

读写原语在 ../store.py；每次写入后自动跑 compile.py 重编译上下文卡和总览。
规则内建于代码：只增不删、编号递增、状态只用枚举词（想法卡片没有状态）。
批量提炼（读长材料做判断）不在本服务里——那是 sync.py + 便宜模型的活。

CLI 零 token 模式：
  python server.py add-idea "想法标题" "一两句正文" "链接文件名,逗号分隔可省"
  python server.py add-decision "决策标题" "背景" "决定" "后果" "已采纳" "依据"
  python server.py add-experiment "实验标题" "假设" "方案" "前置"
  python server.py set-status H1 验证中 "备注可省"
  python server.py get-context
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import store  # noqa: E402


def _recompile():
    import compile as C
    return C.run()


def add_idea(title: str, body: str = "", links: str = "") -> str:
    """往 ideas/ 追加一张卡片（无状态无归属）。links 填索引/卡片文件名，逗号分隔，可省。"""
    ls = [x.strip() for x in links.replace("，", ",").split(",") if x.strip()]
    r = store.add_card(title, body, [store.resolve(l) for l in ls])
    _recompile()
    return r


def add_decision(title: str, background: str = "", decision: str = "",
                 consequence: str = "", status: str = "已采纳", basis: str = "") -> str:
    """往 decisions/ 新建一条 ADR，编号自动递增。状态：建议中/已采纳/已被取代/已废弃。"""
    r = store.add_adr(title, background, decision, consequence, basis, status)
    _recompile()
    return r


def add_experiment(title: str, hypothesis: str = "", plan: str = "", depends: str = "") -> str:
    """往 process/ 今天的日文件登记一个实验，编号自动分配。"""
    r = store.add_entry("E", title, {"假设": hypothesis, "前置": depends, "方案": plan})
    _recompile()
    return r


def set_status(target: str, status: str, note: str = "") -> str:
    """改状态：target 支持 adr-005 / E2 / H1 / R1（想法卡片没有状态）。"""
    r = store.set_status(target, status, note)
    _recompile()
    return r


def get_context() -> str:
    """返回上下文卡全文（编译产物）。新对话开始时调用。"""
    return store.CARD.read_text(encoding="utf-8")


def selftest():
    """在临时副本上验证各操作，不动真实三库。"""
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    for src, name in ((store.D_DIR, "decisions"), (store.P_DIR, "process"), (store.I_DIR, "ideas")):
        if src.exists():
            shutil.copytree(src, tmp / name)
    if store.NORTH.exists():
        shutil.copy(store.NORTH, tmp / "方向.md")
    store.D_DIR, store.P_DIR, store.I_DIR = tmp / "decisions", tmp / "process", tmp / "ideas"
    store.BASE, store.NORTH, store.LOCK = tmp, tmp / "方向.md", tmp / ".写入锁"
    store.CARD, store.OVERVIEW = tmp / "上下文卡.md", tmp / "总览.md"

    r = add_idea("selftest 想法", "正文一句")
    assert "已记录" in r, r
    r = add_decision("selftest 决策", "bg", "dec", "cons", "已采纳", "basis")
    assert "ADR-0009 已记录" in r, r
    assert add_decision("selftest 决策").startswith("已存在同题")        # 标题查重
    assert store.add_adr("x", status="🟡").startswith("非法状态")
    r = add_experiment("selftest 实验", "H1 …", "v1", "E1")
    assert "已登记" in r, r
    eid = r.split()[0]                                                  # 如 E3
    assert store.fill_result(eid, "结果数字", "H1 成立").startswith(eid)
    assert store.set_status("H1", "验证中", "selftest").startswith("H1 状态改为 验证中")
    assert store.set_status("adr-1", "已废弃").startswith("ADR-0001 状态改为 已废弃")
    assert store.set_status("idea-1", "已读").startswith("无法识别目标")  # 想法无状态
    assert store.set_status("X9", "成立").startswith("无法识别目标")
    assert store.set_status("H1", "进行中").startswith("非法状态")
    import datetime
    today_f = tmp / "process" / f"{datetime.date.today():%Y-%m-%d}.md"
    assert f"## {eid} ·" in today_f.read_text(encoding="utf-8")
    assert any("selftest 想法" in f.read_text(encoding="utf-8") for f in (tmp / "ideas").glob("*.md"))
    assert get_context().startswith("# ")
    print("selftest OK（临时目录", tmp, "）")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        cmd, args = sys.argv[1], sys.argv[2:]
        fn = {"add-idea": add_idea, "add-decision": add_decision, "add-experiment": add_experiment,
              "set-status": set_status, "get-context": get_context}.get(cmd)
        print(fn(*args) if fn else __doc__)
    else:
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("research-log")
        mcp.tool()(get_context)
        mcp.tool()(add_idea)
        mcp.tool()(add_decision)
        mcp.tool()(add_experiment)
        mcp.tool()(set_status)
        mcp.run()
