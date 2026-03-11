## TLDR

- 不同治理制度可以统一抽象为：`Pattern（消息流拓扑） + Feature（可叠加特性）`。
- 4 类核心 Pattern：`Pipeline`、`Gated Pipeline`、`Autonomous Cluster`、`Consensus`。
- 实验阶段优先选各 Pattern 的 Representative 制度：雅典民主,秦汉郡县,唐朝三省六部,蒙古帝国,美国联邦,苏联

# MAS 架构模式报告

**—— 从多智能体系统工程视角重新审视 28 种治理制度**

## 第一部分：四种核心 Pattern 定义

### Pattern A：Pipeline（单链管道）

```
User ──→ Planner ──→ [Manager] ──→ Executor ──→ Output
```

**拓扑定义：** 消息单向流动，从 User 到 Executor，无回路。中间可以有扇出（一对多分发），但没有任何独立节点能让消息"往回走"或阻断流程。

**核心判定标准：** 系统中不存在拥有 reject/veto 权限的独立节点。如果一个"审核者"存在但没有 reject 权限、或 enabled=false、或只做日志记录，它在拓扑上不存在。

**User 位置：** 系统入口。User 发出 Prompt，等最终 Output，中间不介入。

**Representative 制度：古埃及法老制。** 法老决定建造金字塔 → 维齐尔制定劳动力和资源方案 → 各省诺姆长官(Nomarch)征调人力物资 → 工程执行 → 完成。全程无任何节点能阻断法老的决策。

---

### Pattern B：Gated Pipeline（门控管道）

```
Initiator ──→ Planner ──→ Gate1 ──→ Gate2 ──→ ... ──→ Executor ──→ [Auditor]
                            │          │                              │
                          可修改     可Veto                       可判无效
                          可Reject   可Reject
```

**拓扑定义：** 管道中插入了一个或多个独立的 Gate 节点，每个 Gate 拥有 reject、veto 或 modify 权限，可以将方案打回、阻断或修改。Auditor 是后置 Gate，不阻止执行但可在执行后判定结果无效。

**核心判定标准：** 存在至少一个独立节点，专门审核上游输出，并且拥有实际的阻断/打回权限。Gate 数量可以是 1 个（如唐代门下省）也可以是多个（如美国的委员会→国会→总统→最高法院）。

**User 位置：** 当只有一个 Gate 时，User 仍在系统入口。当 Gate 数量增多，User 的职能（发起、审批、终审）被拆散到多个节点，没有单一 User。

**Representative 制度：美国联邦总统制。** 议员提出法案 → 委员会审议修改(Gate1: modify) → 参众两院投票(Gate2: approve/reject) → 总统签署或否决(Gate3: veto) → 法律生效执行 → 最高法院可判定违宪(Auditor: invalidate)。Gate 类型最丰富，拓扑最完整。

---

### Pattern C：Autonomous Cluster（自治子系统集群）

```
User ──→ Orchestrator
              │
     ┌────────┼────────┐
     ▼        ▼        ▼
  [Sub-A]  [Sub-B]  [Sub-C]   ← 各自内部闭环
     │        │        │
     └────────┼────────┘
              ▼
           汇总 → User
```

**拓扑定义：** User 发出任务 → Orchestrator 拆解分发 → 多个自治子系统各自内部闭环处理 → 结果汇总回 User。每个子系统有自己的 Planner 和 Executor，Orchestrator 只负责"分活"和"收活"。

**核心判定标准：** 子系统内部有独立决策能力，不是简单的执行节点。Orchestrator 的控制强度是配置项（无控制 / 心跳 / 命令），不影响 Pattern 归属。

**User 位置：** 系统入口 + 最终汇总接收端。

**Representative 制度：江户幕藩体制。** 幕府颁布政策 → 各藩大名在藩内自主治理（有自己的家臣团、税收、司法） → 大名须定期参觐交代（到江户居住）向幕府报告 → 幕府汇总监控。心跳机制（参觐交代）使自治与管控的张力最清晰。

---

### Pattern D：Consensus（共识驱动）

```
Planner (可随机) ──→ Consensus Layer [Agent1][Agent2]...[AgentN] ──→ Executor
                         投票 / 协商 / 全员一致
```

**拓扑定义：** Planner 生成方案 → 提交给一组 Agent 进行集体决策 → 通过后执行。决策权不在任何单一节点，而在集体。

**核心判定标准：** 决策由一组平等（或加权）的 Agent 通过投票/协商做出，且投票结果具有约束力。如果协商只是咨询性的（如哈里发制的 Shura），不算 Consensus。

**User 位置：** User 就是 Consensus Layer 本身——不是单个节点，而是一组 Agent 的集体行为。

**Representative 制度：雅典直接民主制。** 五百人议事会（随机抽签产生）准备议题 → 公民大会全体公民投票（多数决） → 当选官员执行 → 陪审法庭可追溯审查。最纯粹的共识决策，Planner 随机化，Consensus Layer 为全体公民。

---

## 第二部分：Feature 清单

Feature 是可叠加的节点级或系统级特性，不改变主链路的消息流拓扑。任何 Pattern 都可以附加任意 Feature。

| Feature                            | 定义                                            | 改变了什么         | 没改变什么                        |
| ---------------------------------- | --------------------------------------------- | ------------- | ---------------------------- |
| **Monitor（旁路监控）**                  | 独立节点以 read-only 权限监察主链路节点行为，发现异常向 User 报告     | 增加了一条旁路信息通道   | 主链路拓扑不变，Monitor 不阻断流程        |
| **Human-in-the-loop Confirmation** | User 在链条中间插入一个确认步骤（如明清朱批）                     | User 可以暂停流程确认 | 不是独立 Reviewer——是 User 自己确认自己 |
| **Delegated User（委托 User）**        | User 把全部执行权委托给代理 Planner，只做最终验收               | User 的介入时机    | 主链路拓扑不变                      |
| **Planner Internal Consensus（Planner 内部共识）** | Planner 节点内部通过协商/集体决策产生输出（如哈里发制 Shura、苏联政治局），可按约束力细分为弱共识/强共识 | Planner 内部实现  | 对外仍输出单一决策，下游看不到内部机制          |
| **递归 Executor**                    | Executor 内部递归实例化子 Executor（如蒙古万→千→百→十）        | Executor 内部结构 | 主链路拓扑不变                      |
| **共享状态（Shared State）**             | 所有节点读写同一个全局状态对象（如印加 Quipu）                    | 状态管理方式        | 消息流方向不变                      |
| **应急模式切换（Emergency Handler）**      | 休眠节点在紧急情况下激活，改变系统运行模式                         | 系统运行模式        | 常态下的拓扑不变                     |
| **硬护栏（System Protocol）**           | 所有节点输出必须通过不可违反的系统级约束检查                        | 输出约束          | 消息流拓扑不变                      |
| **随机化 Planner**                    | Planner 由随机抽选产生（如雅典抽签）                        | Planner 选择方式  | Planner 在拓扑中的位置不变            |
| **Symbolic Trigger（象征性触发）**        | 某节点仅提供合法性 Token，不做实质判断（如英国君主御准）               | 无实质影响         | 主链路拓扑不变                      |
| **节点生命周期控制**                       | 外部角色控制节点的任免（如易洛魁氏族母亲）                         | 节点人事权         | 运行时消息流不变                     |
| **Consensus Gate**                 | Gated Pipeline 中某个 Gate 内部采用投票机制（如斯巴达 Apella） | Gate 内部决策方式   | 该 Gate 在管道中的拓扑位置不变           |

---

## 第三部分：28 个制度逐一分析

### Pattern A：Pipeline（13 个制度）

---

#### A1. 古埃及法老制 ★ Representative

**Pattern：Pipeline**

**为什么：** 法老拥有绝对权力，维齐尔和地方官员是纯执行节点，不存在任何独立的审核或阻断机制。

**执行流程（建造金字塔）：**
法老决定建造 → 维齐尔(Vizier)制定劳动力征调和资源分配方案 → 各省诺姆长官(Nomarch)接收指令并在辖区内组织执行 → 工匠和劳工完成建造 → 成果呈报法老。全程单向流动，无回路。

**Feature：** 无。这是最纯粹的 Pipeline。

---

#### A2. 罗马帝国元首制

**Pattern：Pipeline**

**为什么：** 元老院在帝制时期已虚化为橡皮图章，不具备实际 reject 权限。皇帝决策直接流向执行层。

**执行流程（皇帝颁布一道行省税收政策）：**
皇帝决策 → 御前顾问团(Consilium Principis)协助拟定细则 → 元老院名义上"审议通过"（实为自动批准） → 行省总督(Proconsul/Legatus)在各行省执行 → 税收上缴国库。元老院环节等价于 `enabled=false` 的 Reviewer 节点。

**Feature：** 无。

---

#### A3. 罗马天主教会圣统制

**Pattern：Pipeline**

**为什么：** 教皇拥有最高且不可挑战的权威（教皇无谬误，1870年正式教义化）。各级教会机构是按领域分工的执行分支，无独立审核权。

**执行流程（教皇颁布一道通谕 Encyclical）：**
教皇决策 → 相关圣部(Dicastery，如信理部)起草文本 → 教皇签署 → 通谕下发至各国主教团 → 主教在教区传达 → 堂区神父向信众宣读执行。多分支扇出，但无回路。

**Feature：** 无。Dicastery 是领域分支（fan-out），不是独立 Gate。

---

#### A4. 阿拉伯-伊斯兰哈里发制

**Pattern：Pipeline**

**为什么：** Shura（协商）是咨询性的，不具有约束力。卡迪(Qadi)的合规判定是 Executor 自带的校验逻辑，不是独立 Reviewer 节点。

**执行流程（哈里发决定发动一次远征）：**
哈里发提出远征计划 → 可召集 Shura 咨询资深圣门弟子意见（但哈里发不受其约束） → 哈里发下令 → 各省总督(Wali)征调军队和物资 → 军事指挥官领兵出征 → 卡迪随军确保行为符合伊斯兰法。Shura 是 Planner 内部的"征求意见"步骤，卡迪是 Executor 的内置校验。

**Feature：** Planner Internal Consensus（弱共识：Shura 咨询性协商）。

---

#### A5. 法国绝对君主制

> **⚠️ 修正说明：** 原报告归为 Pipeline（Reviewer disabled）。经验证，高等法院(Parlement)在路易十五、十六时期拥有实际的 reject 权（谏诤权 droit de remontrance），多次阻挡税改。但考虑到路易十四时期确实压制了高等法院，且国王可通过御座裁判(lit de justice)强制覆盖，本制度处于 **Pipeline 与 Gated Pipeline 的边界**。
> 
> **最终判定：Gated Pipeline（见 B2）。** 理由：高等法院的 reject 权在制度设计上存在，国王的强制覆盖是非常规手段（类似唐代皇帝强制覆盖门下省封驳）。如果唐三省六部因封驳权算 Gated Pipeline，法国高等法院同理。

---

#### A5（实际编号）. 奥斯曼帝国御前会议制

**Pattern：Pipeline**

**为什么：** 苏丹将全部执行权委托给大维齐尔。御前会议(Divan)是大维齐尔主持的多专家协作，属于 Planner 内部实现（Mixture of Experts），不是独立拓扑节点。

**执行流程（发动一次对外战争）：**
苏丹表达战略意图 → 大维齐尔在御前会议(Divan)中与军事大臣、财政大臣、大法官协商制定方案 → 大维齐尔拍板 → 各省帕夏(Pasha)征调军队 → 近卫军(Janissary)和地方部队集结出征 → 战果呈报苏丹验收。苏丹只在起点和终点出现。

**Feature：** 委托 User（苏丹 delegate 给大维齐尔）。

---

#### A6. 明清内阁制与军机处

**Pattern：Pipeline**

**为什么：** 皇帝朱批是 User 确认自己的决策，不是独立 Reviewer。清代军机处更是皇帝的私人秘书班子，无独立判断权。

**执行流程（明代：处理一份边疆军情奏报）：**
边疆奏报送达 → 内阁大学士阅读并"票拟"（草拟处理意见） → 呈送皇帝 → 皇帝"朱批"（用红笔批示同意/修改/否决） → 批准后交六部执行 → 六部下达各省。朱批是 User 在链条中间的确认步骤，等价于 `User.confirm(plan)`。

> **边界注意：** 明代前中期六科给事中拥有封驳权，可以驳回皇帝诏令退回重拟，这在结构上类似唐代门下省。但六科给事中的权力在明中后期逐渐萎缩，到清代完全消失。将明清合并处理时，整体归为 Pipeline 是合理的，但需注意明代前中期存在 Gated Pipeline 的要素。

**Feature：** Human-in-the-loop Confirmation（朱批）。

---

#### A7. 苏联共产党-国家体制

**Pattern：Pipeline**

**为什么：** 最高苏维埃虚化为橡皮图章。政治局是实际决策核心，但它是 Planner 节点的内部实现——对外输出单一决策，下游（部长会议、国家计委、各部委）按指令执行，不存在独立的外部审核节点。

**执行流程（推行一项全国性经济政策，如赫鲁晓夫的玉米种植运动）：**
赫鲁晓夫在政治局提出政策 → 政治局内部讨论（有争论但最终通过） → 部长会议制定实施方案 → 国家计委(Gosplan)分配资源指标 → 各加盟共和国/州执行 → 最高苏维埃事后追认（形式性投票，100%通过）。

**Feature：** Planner Internal Consensus（强共识：政治局集体决策机制；1964年政治局投票罢免赫鲁晓夫本人即为此机制的极端运用）。

---

#### A8. 波斯阿契美尼德行省制

**Pattern：Pipeline**

**为什么：** 主链路是经典的单向管道（国王→总督→执行）。"国王之眼"是旁路监察，不阻断主流程。

**执行流程（国王下令各行省缴纳年贡）：**
大王决策年贡标准 → 御前书记官拟定诏令 → 各行省总督(Satrap)接收指令并在辖区内征收 → 贡赋运往波斯波利斯。与此同时，"国王之眼"(王室监察官)不定期巡查各行省 → 发现总督贪腐或不服从则直接向大王报告 → 大王决定是否撤换总督。两条信息流平行运作。

**Feature：** Monitor（"国王之眼"，主动巡查+报告，不阻断主链路）。

---

#### A9. 秦汉郡县制

**Pattern：Pipeline**

**为什么：** 主链路是皇帝→丞相→郡县的单向管道。御史大夫系统独立运行，但只能弹劾报告，不能直接阻断政令执行——最终裁决权在皇帝。

**执行流程（皇帝推行一项新税制）：**
皇帝决策 → 丞相府制定实施细则 → 太尉府（如涉及军事）配合 → 诏令下达各郡太守 → 各县令在辖区执行。与此同时，御史大夫派遣监御史巡查各郡 → 发现地方官吏执行不力或贪腐 → 上奏皇帝弹劾 → 皇帝决定是否追究，交廷尉审理。

**Feature：** Monitor（御史大夫系统，主动监察+弹劾报告，不直接阻断主链路）。

---

#### A10. 蒙古帝国札撒与汗国制

**Pattern：Pipeline**

**为什么：** 消息流本身是经典单链管道（大汗→逐级执行）。特殊性在于 Executor 层的递归结构。

**执行流程（大汗下令征调十万骑兵）：**
大汗下令 → 万户长(Tümen)各领命征调一万人 → 每个万户长指令下属十个千户长(Mingghan)各征一千人 → 每个千户长指令十个百户长(Jaghun)各征一百人 → 每个百户长指令十个十户长(Arban)各征十人 → 十户长通知各户出征。每级 1:10 递归分解，末端汇总回报完成情况。

**Feature：** 递归 Executor（每级 1:10 递归实例化子 Executor）。

---

#### A11. 印加帝国米塔劳役制

**Pattern：Pipeline**

**为什么：** 消息流是单向管道，类似蒙古的递归结构。特殊性在于全局共享状态（Quipu 结绳记事）。

**执行流程（萨帕·印卡下令修建一段皇家道路）：**
萨帕·印卡决策 → 四区总督(Suyuyuq Apu)分配任务到所辖大区 → 省级管理者细化 → 地方库拉卡(Kuraka)从辖区征调米塔劳役人口 → 劳工修建道路。所有层级通过 Quipu（结绳记事）记录劳动力调配、物资消耗、完成进度，Quipu 信息可被任意层级读取。

**Feature：** 递归 Executor + 共享状态（Quipu，所有节点读写同一状态对象）。

---

#### A12. 苏美尔城邦制

**Pattern：Pipeline**

**为什么：** 常态下是恩西(Ensi)主导的单链管道。特殊性在于紧急状态下系统会切换运行模式。

**执行流程（常态：城邦管理灌溉工程）：**
恩西(城邦领主)决策 → 神庙官僚制定灌溉分配方案 → 各区执行。

**执行流程（紧急：外敌入侵）：**
公民大会紧急召开 → 选出卢伽尔(Lugal，军事领袖) → 卢伽尔获得全权指挥权 → 征调全城壮丁应战 → 战争结束后卢伽尔交权（理论上），恢复常态模式。

**Feature：** 应急模式切换（Emergency Handler——休眠节点"公民大会"在紧急时激活，临时改变系统运行模式和权力结构）。

---

#### A13. 马里帝国曼丁卡治理制

**Pattern：Pipeline**

**为什么：** 消息流是经典的单链管道（曼萨→地方官→执行）。特殊性在于所有决策受不可违反的宪法级约束。

**执行流程（曼萨处理一起领地纠纷）：**
曼萨(国王)接到纠纷报告 → 曼萨或其代理人做出裁决 → 裁决必须符合曼丁卡宪章(Kouroukan Fouga)的基本原则（如特定氏族的世袭职业权不可剥夺） → 如果裁决违反宪章，则被视为非法 → 各省法里(Farin，总督)在辖区内执行裁决。世袭专业化的工匠、商人、格里奥特(Griot)等按各自职能分工完成具体事务。

**Feature：** 硬护栏（曼丁卡宪章，所有节点输出必须通过 `SystemProtocol.validate()` 检查）。

---

### Pattern B：Gated Pipeline（7 个制度）

---

#### B1. 唐代三省六部制

**Pattern：Gated Pipeline**

**为什么：** 门下省是独立节点，专门审核中书省的诏令输出，并拥有实际的封驳（reject）权限，可将诏令打回中书省重写。

**执行流程（皇帝要颁布一道新法令）：**
皇帝授意 → 中书省(Planner)起草诏令 → 诏令送交门下省(Gate)审核 → 门下省侍中审阅，如认为不妥则"封驳"退回中书省重写 → 中书省修改后重新提交 → 门下省通过 → 尚书省接收 → 六部(Executor)按职能分工执行。封驳可能经历多轮，但皇帝可以强制覆盖门下省（非常规手段）。

**Gate 清单：** 门下省（1个 Gate，类型：reject，可触发重写回路）。

**Feature：** 无。这是最纯粹的单 Gate 管道。

---

#### B2. 法国绝对君主制

**Pattern：Gated Pipeline**

**为什么：** 高等法院(Parlement)拥有谏诤权(droit de remontrance)，可以拒绝登记国王敕令并将其打回。这与唐代门下省的封驳在结构上同构。

**执行流程（路易十五推行新税收政策）：**
国王与御前会议决策 → 大法官(Chancelier)起草敕令 → 敕令送交巴黎高等法院(Parlement de Paris)登记 → 高等法院审查，如反对则发回"谏诤书"(remontrance) → 国王可以修改敕令重新提交 → 如果高等法院仍然拒绝，国王可召开御座裁判(lit de justice)亲临法院强制登记 → 登记后，各省总督(Intendant)执行。

**Gate 清单：** 高等法院（1个 Gate，类型：reject，可被国王 override）。

> **时期差异：** 路易十四时期高等法院被有效压制（Gate 接近 disabled），此时系统退化为 Pipeline。路易十五/十六时期高等法院非常活跃，多次实质性阻挡税改。制度设计上 Gate 存在，实际运行取决于国王的强势程度。

**Feature：** 无。

---

#### B3. 罗马共和国混合立宪制

**Pattern：Gated Pipeline**

**为什么：** 议案从执政官到最终执行需经过多个独立的 Gate 节点，每个 Gate 拥有不同类型的权限。保民官的 veto 权是整个体系中最强的阻断机制。

**执行流程（执政官提出一项新法案）：**
执政官(Consul)提出法案 → 元老院(Senatus)审议讨论，可修改法案内容(Gate1: modify) → 修改后的法案提交人民大会(Comitia)投票，只能整体通过或否决(Gate2: binary approve/reject) → 在以上任何环节中，保民官(Tribunus Plebis)可以行使一票否决权(Gate3: veto，一键全局中断) → 通过后由相关官员执行。

**Gate 清单：** 元老院(modify) + 人民大会(binary approve/reject) + 保民官(veto)。

**Feature：** 无。

---

#### B4. 英国议会君主制

**Pattern：Gated Pipeline**

**为什么：** 法案必须经过下院和上院两个独立 Gate 的审议和投票。国王御准在现代是纯形式性的。

**执行流程（首相推动一项新法案）：**
首相/内阁(Initiator)提出法案 → 下院(House of Commons)辩论、修改、投票(Gate1: modify + approve/reject) → 上院(House of Lords)辩论、可提出修正案送回下院(Gate2: modify + approve/reject，但下院可通过《议会法》绕过上院) → 国王御准(Royal Assent，Symbolic Trigger，300多年未被拒绝过) → 法律生效执行。

**Gate 清单：** 下院(modify + approve/reject) + 上院(modify + approve/reject，可被绕过)。无 Auditor（议会主权原则下，法院不能宣布议会法案无效）。

**Feature：** Symbolic Trigger（国王御准，仅提供合法性 Token）。

---

#### B5. 美国联邦总统制 ★ Representative

**Pattern：Gated Pipeline**

**为什么：** Gate 数量最多、类型最丰富（modify + approve/reject + veto + invalidate），是 Gated Pipeline 的最完整体现。

**执行流程（一项联邦法案从提出到生效）：**
议员(Initiator)提出法案 → 相关委员会(Committee)审议、听证、修改(Gate1: modify，大量法案在此阶段被搁置) → 参议院/众议院全体投票(Gate2: approve/reject，需两院分别通过) → 法案送交总统(Gate3: sign/veto，总统可否决，国会可以 2/3 多数推翻否决) → 签署后法律生效，行政机构执行 → 任何公民或机构可挑战法律合宪性，最高法院(Auditor)可判定违宪使法律无效。

**Gate 清单：** 委员会(modify) + 参众两院(approve/reject) + 总统(veto) + 最高法院(Auditor: invalidate)。

**Feature：** 无。

---

#### B6. 欧洲联盟超国家治理体制

**Pattern：Gated Pipeline**

**为什么：** 立法过程需要欧洲议会和部长理事会的共同决定（co-decision），两者都有实质修改和否决权。欧洲法院是 Auditor。

**执行流程（欧盟委员会推动一项新法规）：**
欧盟委员会(Initiator/Planner)提出法规草案 → 欧洲议会(European Parliament)一读审议修改(Gate1: modify + approve/reject) → 部长理事会(Council of Ministers)审议，可接受或提出修正(Gate2: modify + approve/reject) → 如两机构意见不一致，进入调解委员会协商 → 达成一致后法规通过 → 各成员国执行 → 欧洲法院(Court of Justice)可裁定法规违反欧盟基本条约(Auditor: invalidate)。

**Gate 清单：** 欧洲议会(modify + approve/reject) + 部长理事会(modify + approve/reject) + 欧洲法院(Auditor: invalidate)。

**Feature：** 无。

---

#### B7. 古斯巴达寡头与民主混合制

> **⚠️ 修正说明：** 原报告归为 Consensus（模式6）。经验证，斯巴达是多层门控结构：Gerousia 预审过滤提案，Apella 只能二元投票（不能修改提案内容），Ephors 拥有超越双王的监督和阻断权。Apella 的投票机制是其中一个 Gate 的内部实现方式，不是系统整体的决策模式。与雅典的根本区别在于：雅典公民大会是主权机构（可以发起、修改、投票），斯巴达 Apella 只能对 Gerousia 提交的提案做二元判定。

**Pattern：Gated Pipeline**

**为什么：** 决策权被分散到多个层级——Gerousia 过滤提案、Apella 投票、Ephors 监督执行并有阻断权。这是典型的多级门控结构。

**执行流程（斯巴达决定对外开战）：**
双王或 Ephors 提出开战议案(Initiator) → 长老院 Gerousia（28名终身长老 + 2名国王，共30人）审议并决定是否将议案提交公民大会(Gate1: filter，不合格的提案直接搁置) → 公民大会 Apella 以呼喊声表决，只能整体通过或否决(Gate2: binary approve/reject) → 通过后，Ephors（5名，每年选举）监督执行过程，有权审判国王、罢免将领、中止政策(Gate3: 持续性 veto/阻断) → 国王领军出征。

**Gate 清单：** Gerousia(filter) + Apella(binary approve/reject) + Ephors(持续性监督 + 阻断权)。

**Feature：** Consensus Gate（Apella 内部采用呼喊投票的共识机制，但它在管道中的角色是一个 Gate，不是系统的主权决策层）。

---

### Pattern C：Autonomous Cluster（5 个制度）

---

#### C1. 中国周代分封制

**Pattern：Autonomous Cluster**

**为什么：** 诸侯国在各自封地内拥有完整的统治权（军队、税收、司法、官僚体系），天子只在理论上是最高权威。诸侯国不是执行天子指令的末端节点，而是内部闭环的自治子系统。

**执行流程（天子要求诸侯出兵勤王）：**
天子发出勤王号令(Orchestrator 广播) → 各诸侯国在国内独立决策是否响应、出多少兵、何时出发 → 愿意响应的诸侯各自征调本国军队 → 诸侯军队集结于约定地点 → 联军作战（天子名义统帅） → 战后各自返回封地。不愿响应的诸侯可以找借口拖延甚至拒绝——天子无有效惩罚手段。

**Orchestrator 控制强度：** 无控制（诸侯可忽略天子号令，如春秋时期常态）。

**Feature：** 无。

---

#### C2. 西欧封建领主制

**Pattern：Autonomous Cluster**

**为什么：** 每个封臣在其领地内拥有独立的司法权、税收权和军事力量，是内部闭环的自治子系统。国王与封臣之间是契约关系，不是命令关系。

**执行流程（国王召集封臣出征）：**
国王(Orchestrator)根据封建契约召集封臣 → 各封臣在领地内独立决定出兵规模和装备 → 封臣率军到达集结点 → 联军作战 → 服役期满（通常40天）后封臣有权撤回。封臣可以谈判条件、讨价还价，国王没有单方面命令权。

**Orchestrator 控制强度：** 无控制/弱控制（基于契约的双向义务）。

**Feature：** 无。

---

#### C3. 神圣罗马帝国

**Pattern：Autonomous Cluster**

**为什么：** 帝国由数百个半独立的邦国组成，皇帝权力极为有限，帝国议会(Reichstag)更多是协商论坛而非指挥机构。各邦内部完全自治。

**执行流程（皇帝试图对奥斯曼帝国发动战争）：**
皇帝在帝国议会(Reichstag)提出战争议案 → 三个院（选帝侯院、诸侯院、城市院）分别讨论 → 即使议会通过，各邦可以拖延、减少贡献或找理由不配合 → 愿意参与的邦国各自组织军队和物资 → 皇帝尝试统筹联军 → 效果取决于各邦的合作意愿。伏尔泰名言"既非神圣，亦非罗马，更非帝国"准确描述了这种松散结构。

**Orchestrator 控制强度：** 极弱（子系统可以忽略 Orchestrator）。

**Feature：** 无。

---

#### C4. 日本江户幕藩体制 ★ Representative

**Pattern：Autonomous Cluster**

**为什么：** 各藩(约260个)在藩内拥有独立的行政、司法、税收权，是内部闭环的自治子系统。但幕府通过参觐交代(Sankin-kōtai)制度强制大名定期到江户居住，形成有效的心跳监控机制。

**执行流程（幕府颁布一项全国性禁令，如锁国令）：**
将军(Orchestrator)通过老中发布锁国政策 → 政策通知各藩大名 → 各藩大名在藩内自行制定具体执行措施（如何管控港口、如何处理外国人） → 各藩按自己的方式执行 → 大名在参觐交代期间向幕府汇报执行情况 → 幕府通过大名在江户的人质家属和目付(监察官)确认各藩合规。如发现严重违规，幕府可"改易"（没收领地）或"减封"。

**Orchestrator 控制强度：** 心跳控制（参觐交代 = 定期 health_check()，不响应则触发惩罚）。

**Feature：** Monitor（目付监察官，旁路监控各藩动态）。

---

#### C5. 阿兹特克三邦同盟

**Pattern：Autonomous Cluster**

**为什么：** 三个城邦（特诺奇蒂特兰、特斯科科、特拉科潘）各自独立治理内部事务，联合行动时按协议协作，类似外部 API 调用。

**执行流程（三邦同盟发动对外征服战争）：**
特诺奇蒂特兰的特拉托阿尼(Tlatoani，最高统治者)提议征服某城邦 → 三邦协商同意 → 各邦独立征调本城军队 → 联军出征，特诺奇蒂特兰通常主导军事指挥 → 征服后战利品按约定比例分配（特诺奇蒂特兰获最大份额） → 被征服城邦成为朝贡附属城邦(Altepetl)，定期缴纳贡赋。附属城邦内部治理不变，只按接口协议(贡赋清单)交付约定物资。

**Orchestrator 控制强度：** 外部 API 式（联盟内三邦按协议协作；附属城邦按接口返回结果）。

**Feature：** 无。

---

### Pattern D：Consensus（3 个制度）

---

#### D1. 雅典直接民主制 ★ Representative

**Pattern：Consensus**

**为什么：** 公民大会(Ekklesia)是主权机构，全体公民直接投票决策，投票结果具有最终约束力。任何公民都可以发言、提出修正案，大会可以修改议题内容。这与斯巴达 Apella 的根本区别在于：雅典公民大会拥有完整的主权（发起+修改+投票），而非仅做二元判定。

**执行流程（雅典决定是否远征西西里）：**
五百人议事会(Boulē，500人随机抽签产生)准备议题并提出初步方案(Planner，随机化) → 公民大会(Ekklesia)召开，全体公民(约30,000人有资格，通常6,000人到场)辩论 → 任何公民可发言、提出修正案 → 举手投票，多数决通过(Consensus: Majority Vote) → 当选将军(Strategos)负责执行远征 → 事后如有公民认为决策受到不当影响，可通过陪审法庭(Dikasteria)追溯审查相关官员。

**共识算法：** Majority Vote（多数决）。

**Feature：** 随机化 Planner（五百人议事会抽签产生）+ Auditor（陪审法庭追溯审查）。

---

#### D2. 原始部落酋邦制

**Pattern：Consensus**

**为什么：** 决策由部落长老/全体成员在议事会上协商达成，没有任何个人能单独做出对部落有约束力的决定。酋长的权威来自共识而非强制力。

**执行流程（部落决定是否迁徙到新的狩猎场）：**
酋长或有威望的长老提出迁徙建议(Planner) → 氏族议事会召开，各家族代表发言讨论 → 有经验的猎人、年长者的意见权重更高 → 通过反复讨论达成共识(Consensus: Weighted，基于威望的加权共识) → 共识达成后全部落行动 → 如果无法达成共识，部落可能分裂，一部分人留下一部分人迁走。

**共识算法：** Weighted Consensus（基于威望/经验的加权共识）。

**Feature：** 无。

---

#### D3. 易洛魁联盟大议事会

**Pattern：Consensus**

**为什么：** 联盟决策要求全员一致(Unanimity)，任何一个部落代表的反对都会阻止决议通过。这是最严格的共识机制。

**执行流程（联盟决定是否与法国人结盟）：**
某部落的代表提出议案 → 议案先在该部落内部讨论形成部落立场 → 联盟大议事会(Grand Council，约50名酋长/代表)召开 → 议案在"兄弟"部落组和"堂兄弟"部落组之间往返讨论 → 必须所有部落一致同意才能通过(Consensus: Unanimity) → 如无法达成一致，议案搁置 → 通过后各部落各自执行。氏族母亲(Clan Mothers)有权任命和罢免代表——她们不直接参与投票，但控制谁能坐在议事席上。

**共识算法：** Unanimity（全员一致，一票否决）。

**Feature：** 节点生命周期控制（氏族母亲控制代表的任免，即控制 Consensus Layer 中 Agent 的生命周期）。

---

## 第四部分：总览表

| #   | 制度        | Pattern            | Gate/共识机制                                            | Feature             |
| --- | --------- | ------------------ | ---------------------------------------------------- | ------------------- |
| 1   | 古埃及法老制 ★  | Pipeline           | —                                                    | —                   |
| 2   | 罗马帝国元首制   | Pipeline           | —                                                    | —                   |
| 3   | 罗马天主教会圣统制 | Pipeline           | —                                                    | —                   |
| 4   | 哈里发制      | Pipeline           | —                                                    | Planner Internal Consensus（弱共识） |
| 5   | 奥斯曼御前会议制  | Pipeline           | —                                                    | 委托User              |
| 6   | 明清内阁制     | Pipeline           | —                                                    | HITL Confirmation   |
| 7   | 苏联体制      | Pipeline           | —                                                    | Planner Internal Consensus（强共识） |
| 8   | 波斯行省制     | Pipeline           | —                                                    | Monitor             |
| 9   | 秦汉郡县制     | Pipeline           | —                                                    | Monitor             |
| 10  | 蒙古札撒制     | Pipeline           | —                                                    | 递归Executor          |
| 11  | 印加米塔制     | Pipeline           | —                                                    | 递归Executor + 共享状态   |
| 12  | 苏美尔城邦     | Pipeline           | —                                                    | 应急模式切换              |
| 13  | 马里帝国      | Pipeline           | —                                                    | 硬护栏                 |
| 14  | 唐代三省六部    | Gated Pipeline     | 门下省(reject)                                          | —                   |
| 15  | 法国绝对君主制   | Gated Pipeline     | 高等法院(reject, 可override)                              | —                   |
| 16  | 罗马共和国     | Gated Pipeline     | 元老院(modify) + 人民大会(approve/reject) + 保民官(veto)       | —                   |
| 17  | 英国议会君主制   | Gated Pipeline     | 下院(modify+vote) + 上院(modify+vote)                    | Symbolic Trigger    |
| 18  | 美国联邦 ★    | Gated Pipeline     | 委员会(modify) + 国会(vote) + 总统(veto) + 最高法院(audit)      | —                   |
| 19  | 欧盟        | Gated Pipeline     | 欧洲议会(co-decision) + 部长理事会(co-decision) + 欧洲法院(audit) | —                   |
| 20  | 斯巴达       | Gated Pipeline     | Gerousia(filter) + Apella(vote) + Ephors(阻断)         | Consensus Gate      |
| 21  | 周代分封      | Autonomous Cluster | Orchestrator: 无控制                                    | —                   |
| 22  | 西欧封建      | Autonomous Cluster | Orchestrator: 弱控制                                    | —                   |
| 23  | 神圣罗马帝国    | Autonomous Cluster | Orchestrator: 极弱                                     | —                   |
| 24  | 江户幕藩 ★    | Autonomous Cluster | Orchestrator: 心跳控制                                   | Monitor             |
| 25  | 阿兹特克三邦同盟  | Autonomous Cluster | Orchestrator: 外部API式                                 | —                   |
| 26  | 雅典民主 ★    | Consensus          | Majority Vote                                        | 随机Planner + Auditor |
| 27  | 原始部落酋邦    | Consensus          | Weighted Consensus                                   | —                   |
| 28  | 易洛魁联盟     | Consensus          | Unanimity                                            | 节点生命周期控制            |

> ★ = 该 Pattern 的 Representative 制度

**统计：** Pipeline 13 + Gated Pipeline 7 + Autonomous Cluster 5 + Consensus 3 = **28 制度全覆盖**。
