"""test_aggregate.py — aggregate.py 最小自测：造记录 → 聚合 → 断言两份产物。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import aggregate
import store

root = Path(tempfile.mkdtemp(prefix="agg_test_"))
store.set_root(root)
store.init()

# 空库也能出两份文件
aggregate.run()
assert (root / "CONTEXT.md").exists() and (root / "OVERVIEW.md").exists()

store.add_decision("冻结慢权重为主线", status="已采纳", decision="任务切换后冻结")
store.add_decision("废弃旧路线", status="已废弃")
store.add_experiment("五任务准确率", hypothesis="H1")
store.set_status("E1", "已完成")
store.fill_result("E1", result="平均准确率 +12%")
store.add_experiment("稀疏更新对照")                     # E2 未开始 → 进 CONTEXT
store.add_hypothesis("冻结可降低遗忘")                    # H1 待验证 → 进 CONTEXT
store.add_reading("Progressive Nets", serves="H1")       # R1 未读 → 进 CONTEXT
store.add_idea("任务分段冻结", "只更新快权重", links=["0001", "E2"])
(root / "inbox" / "diary.md").write_text("今天想法……", encoding="utf-8")

aggregate.run()
ctx = (root / "CONTEXT.md").read_text(encoding="utf-8")
ovw = (root / "OVERVIEW.md").read_text(encoding="utf-8")

# CONTEXT 只装当前状态
assert "[0001](decisions/0001.md)" in ctx
assert "0002" not in ctx                    # 已废弃决策不进
assert "稀疏更新对照" in ctx and "冻结可降低遗忘" in ctx and "Progressive Nets" in ctx
assert "五任务准确率" not in ctx             # 已完成实验不进
assert "任务分段冻结" in ctx                  # 近 7 天卡片进

# OVERVIEW 装全量、链接可点、有引用索引和 inbox 提醒
assert "五任务准确率" in ovw and "废弃旧路线" in ovw
assert "[E2](logbook/" in ovw and "[0002](decisions/0002.md)" in ovw
assert "引用索引" in ovw and "←" in ovw
assert "待处理 1" in ovw
assert "勿手改" in ctx and "勿手改" in ovw

print("全部通过")
