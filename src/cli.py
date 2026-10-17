"""cli.py — 命令行入口：记一条 / 改状态 / 回填 / 强制聚合。零 token。"""
from __future__ import annotations

import argparse
import sys

import aggregate
import store


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cli.py", description="科研记录系统命令行")
    p.add_argument("--root", default=None, help="库根目录（默认脚本所在目录）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("adr", help="新决策")
    s.add_argument("--title", required=True)
    s.add_argument("--status", default="建议中")
    s.add_argument("--context", default="")
    s.add_argument("--decision", default="")
    s.add_argument("--consequence", default="")
    s.add_argument("--basis", default="")

    s = sub.add_parser("exp", help="新实验")
    s.add_argument("--title", required=True)
    s.add_argument("--status", default="未开始")
    s.add_argument("--hypothesis", default="")
    s.add_argument("--plan", default="")
    s.add_argument("--prior", default="")

    s = sub.add_parser("hyp", help="新假设")
    s.add_argument("--title", required=True)
    s.add_argument("--status", default="待验证")
    s.add_argument("--verify", default="")

    s = sub.add_parser("read", help="新阅读")
    s.add_argument("--title", required=True)
    s.add_argument("--status", default="未读")
    s.add_argument("--serves", default="")

    s = sub.add_parser("idea", help="新卡片")
    s.add_argument("--title", required=True)
    s.add_argument("--text", default="")
    s.add_argument("--link", action="append", default=[])

    s = sub.add_parser("status", help="改某条状态")
    s.add_argument("ref")
    s.add_argument("new_status")

    s = sub.add_parser("result", help="回填结果/结论")
    s.add_argument("ref")
    s.add_argument("--result", default="")
    s.add_argument("--conclusion", default="")

    sub.add_parser("build", help="强制重新聚合")
    return p


ADDERS = {
    "adr": lambda a: store.add_decision(a.title, status=a.status, context=a.context,
                                        decision=a.decision, consequence=a.consequence,
                                        basis=a.basis),
    "exp": lambda a: store.add_experiment(a.title, status=a.status, hypothesis=a.hypothesis,
                                          plan=a.plan, prior=a.prior),
    "hyp": lambda a: store.add_hypothesis(a.title, status=a.status, verify=a.verify),
    "read": lambda a: store.add_reading(a.title, status=a.status, serves=a.serves),
    "idea": lambda a: store.add_idea(a.title, a.text, links=a.link),
}


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.root:
        store.set_root(args.root)
    store.init()
    try:
        if args.cmd in ADDERS:
            rid = ADDERS[args.cmd](args)
            aggregate.run()
            path, _ = store.resolve(rid)
            print(f"已写入 {path.relative_to(store.ROOT).as_posix()} 新记录 {rid}，聚合已刷新")
        elif args.cmd == "status":
            store.set_status(args.ref, args.new_status)
            aggregate.run()
            print(f"{args.ref} 状态已改为 {args.new_status}，聚合已刷新")
        elif args.cmd == "result":
            store.fill_result(args.ref, result=args.result, conclusion=args.conclusion)
            aggregate.run()
            print(f"{args.ref} 已回填结果/结论，聚合已刷新")
        else:  # build
            print(f"聚合完成：{aggregate.run()}")
        return 0
    except (ValueError, KeyError) as e:
        print(f"未写入：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
