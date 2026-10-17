"""research-log MCP server（三库版）

让任何支持 MCP 的 AI 客户端（Cherry Studio / Claude Desktop / Claude Code）直接读写
科研记录三库（decisions/ process/ ideas/）。stdio 传输，无状态。

读写原语在 ../store.py；每次写入后自动跑 compile.py 重编译上下文卡和总览。
规则内建于代码：只增不删、编号递增、只换状态图标。
批量提炼（读长材料做判断）不在本服务里——那是 sync.py + 便宜模型的活。

CLI 零 token 模式：
  python server.py add-idea "想法内容" "A归属如adr-006"
  python server.py set-status H1 🟨 "备注可省"
  python server.py add-decision "决策" "依据"
  python server.py get-context
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import store  # noqa: E402


def _recompile():
    import compile as C
    return C.run()


def add_idea(title: str, owner: str = "", status: str = "🟡", body: str = "") -> str:
    """往 ideas/ 追加一张卡片。owner 填归属（adr-NNN / H? / D?），定不了留空。"""
    r = store.add_idea(title, body, status, owner)
    _recompile()
    return r


def add_decision(title: str, background: str = "", decision: str = "",
                 consequence: str = "", status: str = "✅", basis: str = "") -> str:
    """往 decisions/ 新建一条 ADR，编号自动递增。"""
    r = store.add_decision(title, background, decision, consequence, status, basis)
    _recompile()
    return r


def add_experiment(eid: str, title: str, hypothesis: str = "", plan: str = "", depends: str = "") -> str:
    """往 process/ 当月文件登记一个实验（CLI/工具均可）。"""
    r = store.add_experiment(eid, title, hypothesis, plan, "⬜", depends)
    _recompile()
    return r


def set_status(target: str, status: str, note: str = "") -> str:
    """改状态：target 支持 adr-005 / idea-3 / E2 / H1 / R1。只换图标，不删内容。"""
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
    store.BASE, store.NORTH = tmp, tmp / "方向.md"
    store.CARD, store.OVERVIEW = tmp / "上下文卡.md", tmp / "总览.md"

    r = add_idea("测试想法", "adr-006", "🟡", "selftest 用")
    assert "测试想法" in r and list((tmp / "ideas").glob("007-*.md"))
    r = add_decision("测试决策", "selftest", "选它", "后果", "✅", "selftest")
    assert "ADR-009" in r, r
    r = add_experiment("E3", "测试实验", "H2 …", "v1 方案", "E2")
    assert "E3 已登记" in r
    r = store.fill_result("E3", "结果数字", "H2 ✅")
    assert "已回填" in r
    assert store.set_status("H1", "🟨", "selftest").startswith("H1 状态改为 🟨")
    month = list(store.P_DIR.glob("*.md"))[0]
    assert "🟨 selftest |" in month.read_text(encoding="utf-8")
    assert store.set_status("adr-001", "❌").startswith("ADR-001 状态改为 ❌")
    assert store.set_status("idea-2", "✅").startswith("idea-2 状态改为 ✅")
    assert store.set_status("X9", "✅").startswith("未找到")
    assert store.set_status("H1", "🤖").startswith("非法状态")
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
