"""test_store.py — store.py 最小自测：临时目录里跑全流程。"""
import tempfile
from pathlib import Path

import store

root = Path(tempfile.mkdtemp(prefix="store_test_"))
store.set_root(root)
store.init()

# --- 五类新增 ---
adr = store.add_decision("冻结慢权重为主线", status="已采纳",
                         context="全参数更新遗忘明显", decision="任务切换后冻结慢权重",
                         consequence="待观察", basis="快慢权重可塑性")
assert adr == "0001" and (root / "decisions" / "0001.md").exists()

e1 = store.add_experiment("冻结慢权重后的五任务准确率", hypothesis="H1", plan="五任务顺序训练")
h1 = store.add_hypothesis("冻结慢权重可降低遗忘")
r1 = store.add_reading("Progressive Nets 论文", serves="H1")
assert (e1, h1, r1) == ("E1", "H1", "R1")

e2 = store.add_experiment("稀疏更新的对照实验")
assert e2 == "E2"  # 编号全局递增
assert len(list((root / "logbook").glob("*.md"))) == 1  # 同日合并进一个文件
day_text = store.get("E1")
assert day_text.count("\n## E") == 2  # 两条实验都在

t1 = store.add_idea("任务分段冻结", "切换后只更新快权重", links=["0001", "E1"])
assert (root / "ideas" / f"{t1}.md").exists()
t2 = store.add_idea("同分钟卡片", "测试撞名顺延")
assert t2 != t1  # 同分钟写入，文件名顺延不覆盖

# --- 状态与回填 ---
store.set_status("E1", "已完成")
assert "- 状态: 已完成" in store.get("E1")
assert "- 状态: 未开始" in store.get("E2")  # 别的条目不受影响

try:
    store.set_status("E1", "完事了")
    raise SystemExit("非法状态没有被拒绝")
except ValueError:
    pass

store.fill_result("E1", result="平均准确率 +12%", conclusion="冻结有效")
text = store.get("E1")
assert "- 结果: 平均准确率 +12%" in text and "- 结论: 冻结有效" in text

try:
    store.fill_result("H1", result="x")
    raise SystemExit("非实验条目竟能回填")
except ValueError:
    pass

# --- 解析与引用 ---
p, ln = store.resolve("E1")
assert p.exists() and ln >= 1
assert store.resolve("0001")[0].name == "0001.md"
idx = store.scan_links()
assert "0001" in idx and any("ideas" in s for s in idx["0001"])
assert "E1" in idx

# --- 只增不删：改状态前后行数不变 ---
before = len(store.get("E2").split("\n"))
store.set_status("E2", "搁置")
after = len(store.get("E2").split("\n"))
assert before == after

print("全部通过")
