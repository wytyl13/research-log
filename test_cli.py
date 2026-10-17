"""test_cli.py — cli.py 最小自测：--root 临时目录跑全子命令。"""
import tempfile
from pathlib import Path

import cli

root = Path(tempfile.mkdtemp(prefix="cli_test_"))

# 五类新增，每条都自动聚合
assert cli.main(["--root", str(root), "exp", "--title", "五任务准确率",
                 "--hypothesis", "H1"]) == 0
assert cli.main(["--root", str(root), "hyp", "--title", "冻结可降低遗忘"]) == 0
assert cli.main(["--root", str(root), "read", "--title", "Progressive Nets",
                 "--serves", "H1"]) == 0
assert cli.main(["--root", str(root), "adr", "--title", "冻结慢权重为主线",
                 "--status", "已采纳"]) == 0
assert cli.main(["--root", str(root), "idea", "--title", "分段冻结", "--text", "只更新快权重",
                 "--link", "0001", "--link", "E1"]) == 0
assert (root / "CONTEXT.md").exists() and (root / "OVERVIEW.md").exists()
assert "五任务准确率" in (root / "CONTEXT.md").read_text(encoding="utf-8")

# 改状态、回填
assert cli.main(["--root", str(root), "status", "E1", "已完成"]) == 0
assert cli.main(["--root", str(root), "result", "E1", "--result", "+12%",
                 "--conclusion", "冻结有效"]) == 0
day = next((root / "logbook").glob("*.md")).read_text(encoding="utf-8")
assert "- 状态: 已完成" in day and "- 结果: +12%" in day

# 拒写路径
assert cli.main(["--root", str(root), "status", "E1", "完事了"]) == 1   # 非法状态
assert cli.main(["--root", str(root), "status", "E9", "进行中"]) == 1   # 无此编号

# 强制聚合
assert cli.main(["--root", str(root), "build"]) == 0

print("全部通过")
