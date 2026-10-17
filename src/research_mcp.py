"""research_mcp.py — MCP 服务（FastMCP stdio）：聊天里说一声，当场记一条。

注册方式见 README。工具只调 store/aggregate，薄壳无逻辑。
"""
from __future__ import annotations

import aggregate
import store
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research-log")


@mcp.tool()
def add_decision(title: str, status: str = "建议中", context: str = "",
                 decision: str = "", consequence: str = "", basis: str = "") -> str:
    """记一条决策（ADR）。status 只能取：建议中/已采纳/已被取代/已废弃。"""
    rid = store.add_decision(title, status=status, context=context, decision=decision,
                             consequence=consequence, basis=basis)
    aggregate.run()
    return f"已记录决策 {rid}"


@mcp.tool()
def add_experiment(title: str, status: str = "未开始", hypothesis: str = "",
                   plan: str = "", prior: str = "") -> str:
    """记一条实验。status 只能取：未开始/进行中/已完成/搁置。
    hypothesis 填假设编号（如 H2），prior 填前置实验编号（如 E4）。"""
    rid = store.add_experiment(title, status=status, hypothesis=hypothesis,
                               plan=plan, prior=prior)
    aggregate.run()
    return f"已记录实验 {rid}"


@mcp.tool()
def add_hypothesis(title: str, status: str = "待验证", verify: str = "") -> str:
    """记一条假设（一句话可证伪表述）。status 只能取：待验证/验证中/成立/不成立/搁置。"""
    rid = store.add_hypothesis(title, status=status, verify=verify)
    aggregate.run()
    return f"已记录假设 {rid}"


@mcp.tool()
def add_reading(title: str, status: str = "未读", serves: str = "") -> str:
    """记一条阅读。status 只能取：未读/在读/已读。serves 填服务哪条线（如 E5/H2）。"""
    rid = store.add_reading(title, status=status, serves=serves)
    aggregate.run()
    return f"已记录阅读 {rid}"


@mcp.tool()
def add_idea(title: str, text: str, links: list[str] | None = None) -> str:
    """记一张想法卡片。links 填相关编号（如 ["0003", "E5"]）。"""
    rid = store.add_idea(title, text, links=links or [])
    aggregate.run()
    return f"已记录卡片 {rid}"


@mcp.tool()
def set_status(ref: str, new_status: str) -> str:
    """改某条记录的状态。ref 如 E5/H2/0003，new_status 必须是该类的固定词。"""
    store.set_status(ref, new_status)
    aggregate.run()
    return f"{ref} 状态已改为 {new_status}"


@mcp.tool()
def fill_result(ref: str, result: str = "", conclusion: str = "") -> str:
    """回填实验的结果/结论。只有实验条目（E 编号）能用。"""
    store.fill_result(ref, result=result, conclusion=conclusion)
    aggregate.run()
    return f"{ref} 已回填结果/结论"


@mcp.tool()
def get(ref: str) -> str:
    """按编号取一条记录的原文（E5/H2/R3/0003/卡片时间戳）。"""
    return store.get(ref)


if __name__ == "__main__":
    mcp.run()  # stdio
