---
id: 10
date: 2026-10-17
status: 🟡
owner: ""
links: []
---

# PR/TwoNN 内在维度探针实测 LLM 隐藏状态

用参与率和 TwoNN 估计器测各层隐藏状态内禀维度，预期 10^1 量级且沿层先升后降（驼峰，与 Valeriani 2023 一致）；代码已起草，可复用 continual_learning 手写模型，为'低维流形'论点提供直接实证。
