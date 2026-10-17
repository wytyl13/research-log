"""test_mcp.py — research_mcp 工具函数最小自测（不走 MCP 协议层）。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import research_mcp as rm
import store

root = Path(tempfile.mkdtemp(prefix="mcp_test_"))
store.set_root(root)
store.init()

assert "E1" in rm.add_experiment("五任务准确率", hypothesis="H1")
assert "H1" in rm.add_hypothesis("冻结可降低遗忘")
assert "R1" in rm.add_reading("Progressive Nets", serves="H1")
assert "0001" in rm.add_decision("冻结慢权重为主线", status="已采纳", decision="冻结")
assert "20" in rm.add_idea("分段冻结", "只更新快权重", links=["0001", "E1"])

assert "已完成" in rm.set_status("E1", "已完成")
assert "回填" in rm.fill_result("E1", result="+12%", conclusion="冻结有效")
assert "五任务准确率" in rm.get("E1")            # 取原文
assert "- 结果: +12%" in rm.get("E1")

# 写完自动聚合
assert (root / "CONTEXT.md").exists() and (root / "OVERVIEW.md").exists()

# 拒写路径：非法状态
try:
    rm.set_status("E1", "完事了")
    raise SystemExit("非法状态没有被拒绝")
except ValueError:
    pass

print("全部通过")
