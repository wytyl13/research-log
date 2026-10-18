# 研究当前状态（aggregate.py 自动聚合，勿手改）

> 生成 2026-10-18 00:45；完结条目与历史见 OVERVIEW.md

## 决策主线

| 编号 | 标题 | 状态 |
| --- | --- | --- |
| [0001](records/decisions/0001.md) | 以 FFN 类脑改造为主线，全局部规则架构为长期推广目标 | 已采纳 |
| [0002](records/decisions/0002.md) | 验证对象是干预效果而非知识定位 | 已采纳 |
| [0003](records/decisions/0003.md) | E0 新领域语料选用 2025 年后医学科普文献 | 已采纳 |
| [0004](records/decisions/0004.md) | Step 5 预训练 vs SFT 对比实验推迟 | 已采纳 |

## 进行中（未完结的实验/假设/阅读）

| 编号 | 标题 | 状态 | 关联 |
| --- | --- | --- | --- |
| [H1](records/logbook/2026-10-18.md) | 同等遗忘量下只更新 FFN 学到的新知识多于只更新 Attention | 待验证 | E2 对照实验：持续预训练中分别只更新 FFN / 只更新 Attention，画 (P,F) 帕累托曲线比较。P=PPL_new(before)-PPL(after)，F=Acc_gen(before)-Acc_gen(after)（lm-eval 通用基准） |
| [H2](records/logbook/2026-10-18.md) | TopK 稀疏更新在同等可塑性下降低灾难性遗忘 | 待验证 | E3：只更新激活最强的 k 个记忆槽（TopK h_i），与稠密更新比较同等 P 下的 F |
| [H3](records/logbook/2026-10-18.md) | 快/慢权重分离加周期巩固进一步降低遗忘 | 待验证 | E4：W=W_slow+W_fast，fast 带衰减更新、周期性巩固进 slow（eta_c 远小于 eta_f），与 TopK 基线比较 |
| [H4](records/logbook/2026-10-18.md) | 精度门控局部规则的性能前沿不劣于反向传播 | 待验证 | E5：用 Δv_i=eta*Pi_i*h_i*epsilon（epsilon 只在本层计算，不经过全网反传）替代 W_out 的反向传播，比较 (P,F) 前沿 |
| [H5](records/logbook/2026-10-18.md) | 全局部规则在流式持续学习中优于反向传播 | 搁置 | D1 长期方向，入口在 H4 成立（闸门 G2）之后 |
| [H6](records/logbook/2026-10-18.md) | LLM 隐藏状态内禀维度沿层先升后降呈驼峰形，量级 10^1 | 待验证 | 对各层最后 token 隐向量用参与率 PR=(Σλ)^2/Σλ^2 与 TwoNN 估计内禀维度（总纲附 PyTorch 实现代码，需约 2000 条多样文本），预期与 Valeriani et al. 2023 一致：环境维度 10^3-10^4 而内禀维度 10^1，支撑 LLM 与大脑同为高维嵌入低维流形 |
| [E1](records/logbook/2026-10-18.md) | E0 数据与评测集：新领域语料+事实问答+固定基准 | 进行中 | H1 |
| [E2](records/logbook/2026-10-18.md) | E1 基线 P-F 帕累托曲线（里程碑 M1） | 未开始 | H1 |
| [E3](records/logbook/2026-10-18.md) | E2 FFN-only vs Attn-only 对照（闸门 G1） | 未开始 | H1、E2 |
| [E4](records/logbook/2026-10-18.md) | E3 TopK 稀疏更新 | 未开始 | H2、E3 |
| [E5](records/logbook/2026-10-18.md) | E4 快/慢权重分离与巩固 | 未开始 | H3、E4 |
| [E6](records/logbook/2026-10-18.md) | E5 局部规则替代 W_out 反向传播（闸门 G2） | 未开始 | H4、E5 |
| [R1](records/logbook/2026-10-18.md) | Parr, Pezzulo & Friston 2022《Active Inference: The Free Energy Principle in Mind, Brain, and Behavior》(MIT Press) | 未读 | T1 理论线（自由能统一目标、精度的理论定义）。重点章节两个 AI 建议不同：Cherry 建议第 2/4/5 章，Gemini 建议直奔第 4 章（生成模型）/第 6 章（离散时间主动推断）/第 7 章（连续时间主动推断）——以纯数学推演章节为主，生物学解剖对应部分可跳过 |
| [R2](records/logbook/2026-10-18.md) | Geva et al. 2021 / Dai et al. 2022 (KN) / Meng et al. 2022 (ROME) / Hase et al. 2023 | 在读 | E2 FFN-only vs Attn-only 对照。已读完 Geva 2021，一句话收获：FFN 本质是 key-value 记忆，键和值都能定位到具体知识 |
| [R3](records/logbook/2026-10-18.md) | Kirkpatrick et al. 2017 (EWC) / McClelland et al. 1995 (CLS 互补学习系统) | 未读 | T1/T3 理论线（EWC 作为自由能特例的统一；快慢分离的生物学源头） |
| [R4](records/logbook/2026-10-18.md) | Whittington & Bogacz 2017 / Millidge et al. 2020 / Rao & Ballard 1999 | 未读 | T4 理论线（预测编码在推理收敛时近似等于 BP 梯度的等价性与偏差；Rao & Ballard 是预测编码最具象的工程实现：分层网络只传残差、局部更新权重） |
| [R5](records/logbook/2026-10-18.md) | Miller, Brincat & Roy 2026 'Analog Cognition and Consciousness'（Journal of Neuroscience 理论综述） | 未读 | D1 类脑长期方向。理论要点：脑波（alpha/beta 门控 gamma）像指挥家组织混合选择性神经元、电场耦合（ephaptic coupling）反作用放电阈值、时空计算、认知=把天文维度压缩成低维结构（赶猫问题）；麻醉证据；作者自认是待检验理论而非定论 |
| [R7](records/logbook/2026-10-18.md) | Lake, Jagadish & Jiang 2026：BBT 混合贝叶斯-联结主义模型（arXiv:2608.22154） | 未读 | 认知科学背景（已读 Gemini 解读）：贝叶斯蒸馏+行为微调两阶段，30M Transformer 在四个概念学习任务上全面优于纯贝叶斯与纯 NN；微调后模型系统性转向更简单假设——人类偏离理想贝叶斯、偏爱简单启发式 |

## 最近想法（近 7 天，全库 8 张）

- [202610180045](records/ideas/202610180045.md) LLM 与大脑的维度定性：高维运行、低维连接
- [202610180046](records/ideas/202610180046.md) 类脑架构缺失的三个算子
- [202610180047](records/ideas/202610180047.md) 精度门控=持续学习的'学多少'旋钮
- [202610180048](records/ideas/202610180048.md) 知识注入：多视角 SFT 或填空式 Cloze SFT，不做单句 CPT
- [202610180049](records/ideas/202610180049.md) RSI 观点定稿：持续学习+社会化演进
- [202610180050](records/ideas/202610180050.md) 摒弃 BP 的数学三模块（远期 D1）
- [202610180051](records/ideas/202610180051.md) 高维类脑与低维 LLM 是分工非替代
- [202610180052](records/ideas/202610180052.md) 脑波=突触网络之上的全局动态路由门控

## 记录方式

- 聊天中用 MCP 工具：add_* / set_status / fill_result / get
- 命令行：`cli.py <子命令>`（零 token）
- 外部材料放 `inbox/`，在 Claude Code 敲 `/import` 批量提炼
