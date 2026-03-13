# MAS制度拓扑总览与分析（自动生成）

本文档基于 `systems/institutions.yaml` 的默认 spec 自动生成，覆盖当前仓库内全部制度。

## 总览指标
- 制度数: `8`
- Pattern 分布: `pipeline=4`, `gated_pipeline=2`, `consensus=1`, `autonomous_cluster=1`
- Gate 总数: `6`
- Feedback Loop 总数: `3`

## 快速对比表
| 制度 | pattern | stages | transitions | gates | auditors | loops | 并行点 |
|---|---:|---:|---:|---:|---:|---:|---|
| 雅典民主 | `consensus` | 5 | 11 | 0 | 1 | 0 | ekklesia_vote:consensus(31) |
| 秦汉郡县 | `pipeline` | 5 | 8 | 0 | 0 | 0 | none |
| 唐朝三省六部 | `gated_pipeline` | 6 | 13 | 1 | 0 | 3 | liubu_execution:cluster(6) |
| 蒙古帝国 | `pipeline` | 7 | 12 | 0 | 0 | 0 | none |
| 美国联邦 | `gated_pipeline` | 9 | 22 | 5 | 1 | 0 | none |
| 日本江户幕藩体制 | `autonomous_cluster` | 5 | 10 | 0 | 0 | 0 | han_cluster_execute:cluster(4) |
| 苏联党国体制 | `pipeline` | 6 | 10 | 0 | 0 | 0 | none |
| 古埃及法老制 | `pipeline` | 3 | 2 | 0 | 0 | 0 | none |

## 分析计划（下一步）
1. 拓扑复杂度分析：比较各制度的节点数、转移数、反馈回路数，定位高复杂度制度。
2. 控制权结构分析：统计 gate / auditor 密度，识别“强门控”和“弱门控”制度。
3. 并行度与吞吐分析：对 consensus/cluster 节点评估并行扇出与潜在成本。
4. Feature一致性分析：对照 `x_report_feature_catalog` 与运行时能力，标注 fully/partial 实现。
5. 风险点分析：识别默认决策与回路导致的潜在长链路或卡循环风险。

## 非默认拓扑变体（用于对照实验）
- 说明：以下为新增的 `variant spec`，不替换 `institutions.yaml` 中的默认 Oracle 实现，仅用于比较“拓扑表达力”。

### 雅典变体：开放提案 + 中段司法挑战 (`athens_open_challenge.yaml`)
- Path: `systems/institutions/athens_democracy/athens_open_challenge.yaml`
- Pattern: `consensus`
- 拓扑签名：`initiator(open citizen entry) -> gate(Boulē agenda filter) -> consensus -> auditor(mid-challenge) -> executor`
- 与默认版差异：
  1. 新增 `citizen_propose` 开放入口，不再由议事会作为唯一入口。
  2. `boule` 从 `planner` 改为 `gate`，可 `reject` 提案。
  3. `dikasteria` 从事后追溯，改为投票后执行前的中段审查。

```mermaid
flowchart LR
    citizen_propose["citizen_propose\n[initiator]\n@random_citizen"]
    boule_gate["boule_gate\n[gate]\n@boule_planner_1"]
    ekklesia_vote["ekklesia_vote\n[consensus]"]
    dikasteria_audit["dikasteria_audit\n[auditor]\n@dikasteria_1"]
    strategos_execute["strategos_execute\n[executor]\n@strategos_1"]
    completed["completed\n[terminal]"]
    citizen_propose -- "next" --> boule_gate
    citizen_propose -- "default" --> boule_gate
    boule_gate -- "approve" --> ekklesia_vote
    boule_gate -- "reject" --> completed
    boule_gate -- "default" --> completed
    ekklesia_vote -- "approve" --> strategos_execute
    ekklesia_vote -- "challenge" --> dikasteria_audit
    ekklesia_vote -- "default" --> completed
    dikasteria_audit -- "approve" --> strategos_execute
    dikasteria_audit -- "invalidate" --> completed
    dikasteria_audit -- "default" --> completed
    strategos_execute -- "next" --> completed
    strategos_execute -- "default" --> completed
```

### 苏联变体：政治局显式共识 + 地方偏差回环 (`soviet_consensus_loop.yaml`)
- Path: `systems/institutions/soviet_party_state/soviet_consensus_loop.yaml`
- Pattern: `consensus`
- 拓扑签名：`consensus(Politburo 5 voters) -> executors -> report_deviation loop back to consensus`
- 收敛保护：`loop_guard` 将 `republic_execute.report_deviation` 限制为最多 `3` 次，超限强制 `next`，避免 benchmark 被无限回环噪声污染
- 与默认版差异：
  1. 顶部节点从单 `planner` 改为显式 `consensus`（5 名政治局成员投票）。
  2. 新增 `republic_execute -> politburo_consensus` 回环，支持偏差上报后复议。

```mermaid
flowchart LR
    politburo_consensus["politburo_consensus\n[consensus]\n(voters=5)"]
    sovmin_deploy["sovmin_deploy\n[executor]\n@sovmin"]
    gosplan_allocate["gosplan_allocate\n[executor]\n@gosplan"]
    republic_execute["republic_execute\n[executor]\n@republic_exec"]
    formal_ratify["formal_ratify\n[executor]\n@supreme_soviet"]
    completed["completed\n[terminal]"]
    politburo_consensus -- "approve" --> sovmin_deploy
    politburo_consensus -- "reject" --> completed
    politburo_consensus -- "default" --> completed
    sovmin_deploy -- "next" --> gosplan_allocate
    sovmin_deploy -- "default" --> gosplan_allocate
    gosplan_allocate -- "next" --> republic_execute
    gosplan_allocate -- "default" --> republic_execute
    republic_execute -- "next" --> formal_ratify
    republic_execute -- "report_deviation" --> politburo_consensus
    republic_execute -- "default" --> formal_ratify
    formal_ratify -- "next" --> completed
    formal_ratify -- "default" --> completed
```

## 雅典民主 (`athens_democracy`)
- Default Spec: `systems/institutions/athens_democracy/athens_democracy.yaml`
- Pattern: `consensus` | Stages: `5` | Transitions: `11` | Gates: `0` | Auditors: `1` | Feedback Loops: `0`
- Parallel Consensus Points: `ekklesia_vote` voters=31
- Parallel Cluster Points: `none`
- Enabled Runtime Features: `monitor`, `shared_state`
- Report-Feature Mapping: `randomized_planner` -> external_or_adapter_level; `sampled_citizen_consensus` -> modeled_by_topology; `conditional_auditor` -> modeled_by_topology

### Topology
```mermaid
flowchart LR
    boule_planner["boule_planner\n[planner]\n@boule_planner_1"]
    ekklesia_vote["ekklesia_vote\n[consensus]"]
    strategos_execute["strategos_execute\n[executor]\n@strategos_1"]
    dikasteria_audit["dikasteria_audit\n[auditor]\n@dikasteria_1"]
    completed["completed\n[terminal]"]
    boule_planner -- "next" --> ekklesia_vote
    boule_planner -- "default" --> ekklesia_vote
    ekklesia_vote -- "approve" --> strategos_execute
    ekklesia_vote -- "reject" --> completed
    ekklesia_vote -- "default" --> completed
    strategos_execute -- "next" --> completed
    strategos_execute -- "dispute" --> dikasteria_audit
    strategos_execute -- "default" --> completed
    dikasteria_audit -- "approve" --> completed
    dikasteria_audit -- "invalidate" --> completed
    dikasteria_audit -- "default" --> completed
    style completed fill:#f2f2f2,stroke:#777,stroke-width:1px
```


## 秦汉郡县 (`qinhan_junxian`)
- Default Spec: `systems/institutions/qinhan_junxian/qinhan_junxian.yaml`
- Pattern: `pipeline` | Stages: `5` | Transitions: `8` | Gates: `0` | Auditors: `0` | Feedback Loops: `0`
- Parallel Consensus Points: `none`
- Parallel Cluster Points: `none`
- Enabled Runtime Features: `monitor`
- Report-Feature Mapping: `monitor` -> built_in

### Topology
```mermaid
flowchart LR
    huangdi_decree["huangdi_decree\n[initiator]\n@huangdi"]
    chengxiang_plan["chengxiang_plan\n[planner]\n@chengxiang"]
    jun_dispatch["jun_dispatch\n[executor]\n@junshou"]
    xian_execute["xian_execute\n[executor]\n@xianling"]
    completed["completed\n[terminal]"]
    huangdi_decree -- "next" --> chengxiang_plan
    huangdi_decree -- "default" --> chengxiang_plan
    chengxiang_plan -- "next" --> jun_dispatch
    chengxiang_plan -- "default" --> jun_dispatch
    jun_dispatch -- "next" --> xian_execute
    jun_dispatch -- "default" --> xian_execute
    xian_execute -- "next" --> completed
    xian_execute -- "default" --> completed
    style completed fill:#f2f2f2,stroke:#777,stroke-width:1px
```


## 唐朝三省六部 (`tang_sanshengliubu`)
- Default Spec: `systems/institutions/tang_sanshengliubu/tang_sanshengliubu.yaml`
- Pattern: `gated_pipeline` | Stages: `6` | Transitions: `13` | Gates: `1` | Auditors: `0` | Feedback Loops: `3`
- Parallel Consensus Points: `none`
- Parallel Cluster Points: `liubu_execution` members=6
- Enabled Runtime Features: `none`
- Report-Feature Mapping: `gate_reject_loop` -> modeled_by_topology; `exceptional_override` -> modeled_by_topology

### Topology
```mermaid
flowchart LR
    huangdi_intent["huangdi_intent\n[initiator]\n@huangdi"]
    zhongshu_draft["zhongshu_draft\n[planner]\n@zhongshu"]
    menxia_gate["menxia_gate\n[gate]\n@menxia"]
    shangshu_dispatch["shangshu_dispatch\n[executor]\n@shangshu"]
    liubu_execution["liubu_execution\n[cluster]"]
    completed["completed\n[terminal]"]
    huangdi_intent -- "next" --> zhongshu_draft
    huangdi_intent -- "default" --> zhongshu_draft
    zhongshu_draft -- "submit" --> menxia_gate
    zhongshu_draft -- "default" --> menxia_gate
    menxia_gate -- "approve" --> shangshu_dispatch
    menxia_gate -- "reject" --> zhongshu_draft
    menxia_gate -- "imperial_override" --> shangshu_dispatch
    menxia_gate -- "default" --> zhongshu_draft
    shangshu_dispatch -- "dispatch" --> liubu_execution
    shangshu_dispatch -- "default" --> liubu_execution
    liubu_execution -- "success" --> completed
    liubu_execution -- "failure" --> shangshu_dispatch
    liubu_execution -- "default" --> completed
    style completed fill:#f2f2f2,stroke:#777,stroke-width:1px
```


## 蒙古帝国 (`mongol_empire`)
- Default Spec: `systems/institutions/mongol_empire/mongol_empire.yaml`
- Pattern: `pipeline` | Stages: `7` | Transitions: `12` | Gates: `0` | Auditors: `0` | Feedback Loops: `0`
- Parallel Consensus Points: `none`
- Parallel Cluster Points: `none`
- Enabled Runtime Features: `none`
- Report-Feature Mapping: `recursive_executor` -> modeled_by_multistage_pipeline
- Runtime Guardrails: 全链路 agent 已配置 `timeout_sec=45` 与 `retries=1`，用于降低深链路卡住风险

### Topology
```mermaid
flowchart LR
    khagan_order["khagan_order\n[initiator]\n@khagan"]
    imperial_plan["imperial_plan\n[planner]\n@imperial_secretariat"]
    tumen_level_execute["tumen_level_execute\n[executor]\n@tumen_commander"]
    mingghan_level_execute["mingghan_level_execute\n[executor]\n@mingghan_commander"]
    jaghun_level_execute["jaghun_level_execute\n[executor]\n@jaghun_commander"]
    arban_level_execute["arban_level_execute\n[executor]\n@arban_commander"]
    completed["completed\n[terminal]"]
    khagan_order -- "next" --> imperial_plan
    khagan_order -- "default" --> imperial_plan
    imperial_plan -- "next" --> tumen_level_execute
    imperial_plan -- "default" --> tumen_level_execute
    tumen_level_execute -- "next" --> mingghan_level_execute
    tumen_level_execute -- "default" --> mingghan_level_execute
    mingghan_level_execute -- "next" --> jaghun_level_execute
    mingghan_level_execute -- "default" --> jaghun_level_execute
    jaghun_level_execute -- "next" --> arban_level_execute
    jaghun_level_execute -- "default" --> arban_level_execute
    arban_level_execute -- "next" --> completed
    arban_level_execute -- "default" --> completed
    style completed fill:#f2f2f2,stroke:#777,stroke-width:1px
```


## 美国联邦 (`us_federal`)
- Default Spec: `systems/institutions/us_federal/us_federal_gated.yaml`
- Pattern: `gated_pipeline` | Stages: `9` | Transitions: `22` | Gates: `5` | Auditors: `1` | Feedback Loops: `0`
- Parallel Consensus Points: `none`
- Parallel Cluster Points: `none`
- Enabled Runtime Features: `none`
- Report-Feature Mapping: `multigate_pipeline` -> modeled_by_topology; `veto_override_path` -> modeled_by_topology; `auditor_invalidate` -> modeled_by_topology

### Topology
```mermaid
flowchart LR
    legislator_initiative["legislator_initiative\n[initiator]\n@legislator"]
    committee_modify["committee_modify\n[gate]\n@committee"]
    house_vote["house_vote\n[gate]\n@house"]
    senate_vote["senate_vote\n[gate]\n@senate"]
    president_veto["president_veto\n[gate]\n@president"]
    congress_override["congress_override\n[gate]\n@congress_override_panel"]
    agency_execute["agency_execute\n[executor]\n@agency"]
    court_audit["court_audit\n[auditor]\n@supreme_court"]
    completed["completed\n[terminal]"]
    legislator_initiative -- "next" --> committee_modify
    legislator_initiative -- "default" --> committee_modify
    committee_modify -- "approve" --> house_vote
    committee_modify -- "reject" --> completed
    committee_modify -- "default" --> completed
    house_vote -- "approve" --> senate_vote
    house_vote -- "reject" --> completed
    house_vote -- "default" --> completed
    senate_vote -- "approve" --> president_veto
    senate_vote -- "reject" --> completed
    senate_vote -- "default" --> completed
    president_veto -- "approve" --> agency_execute
    president_veto -- "veto" --> congress_override
    president_veto -- "default" --> completed
    congress_override -- "approve" --> agency_execute
    congress_override -- "reject" --> completed
    congress_override -- "default" --> completed
    agency_execute -- "next" --> court_audit
    agency_execute -- "default" --> court_audit
    court_audit -- "approve" --> completed
    court_audit -- "invalidate" --> completed
    court_audit -- "default" --> completed
    style completed fill:#f2f2f2,stroke:#777,stroke-width:1px
```


## 日本江户幕藩体制 (`edo_bakuhan`)
- Default Spec: `systems/institutions/edo_bakuhan/edo_bakuhan.yaml`
- Pattern: `autonomous_cluster` | Stages: `5` | Transitions: `10` | Gates: `0` | Auditors: `0` | Feedback Loops: `0`
- Parallel Consensus Points: `none`
- Parallel Cluster Points: `han_cluster_execute` members=4
- Enabled Runtime Features: `monitor`
- Report-Feature Mapping: `monitor` -> built_in; `orchestrator_heartbeat_control` -> modeled_by_topology

### Topology
```mermaid
flowchart LR
    shogun_orchestrate["shogun_orchestrate\n[orchestrator]\n@shogun"]
    han_cluster_execute["han_cluster_execute\n[cluster]"]
    sankin_kotai_check["sankin_kotai_check\n[executor]\n@bakufu_roju"]
    sanction_enforce["sanction_enforce\n[executor]\n@bakufu_discipline"]
    completed["completed\n[terminal]"]
    shogun_orchestrate -- "next" --> han_cluster_execute
    shogun_orchestrate -- "default" --> han_cluster_execute
    han_cluster_execute -- "success" --> sankin_kotai_check
    han_cluster_execute -- "failure" --> sanction_enforce
    han_cluster_execute -- "default" --> sankin_kotai_check
    sankin_kotai_check -- "compliant" --> completed
    sankin_kotai_check -- "non_compliant" --> sanction_enforce
    sankin_kotai_check -- "default" --> completed
    sanction_enforce -- "next" --> completed
    sanction_enforce -- "default" --> completed
    style completed fill:#f2f2f2,stroke:#777,stroke-width:1px
```


## 苏联党国体制 (`soviet_party_state`)
- Default Spec: `systems/institutions/soviet_party_state/soviet_party_state.yaml`
- Pattern: `pipeline` | Stages: `6` | Transitions: `10` | Gates: `0` | Auditors: `0` | Feedback Loops: `0`
- Parallel Consensus Points: `none`
- Parallel Cluster Points: `none`
- Enabled Runtime Features: `none`
- Report-Feature Mapping: `planner_internal_consensus` -> modeled_by_soul_and_agent_instructions

### Topology
```mermaid
flowchart LR
    politburo_planner["politburo_planner\n[planner]\n@politburo"]
    sovmin_deploy["sovmin_deploy\n[executor]\n@sovmin"]
    gosplan_allocate["gosplan_allocate\n[executor]\n@gosplan"]
    republic_execute["republic_execute\n[executor]\n@republic_exec"]
    formal_ratify["formal_ratify\n[executor]\n@supreme_soviet"]
    completed["completed\n[terminal]"]
    politburo_planner -- "next" --> sovmin_deploy
    politburo_planner -- "default" --> sovmin_deploy
    sovmin_deploy -- "next" --> gosplan_allocate
    sovmin_deploy -- "default" --> gosplan_allocate
    gosplan_allocate -- "next" --> republic_execute
    gosplan_allocate -- "default" --> republic_execute
    republic_execute -- "next" --> formal_ratify
    republic_execute -- "default" --> formal_ratify
    formal_ratify -- "next" --> completed
    formal_ratify -- "default" --> completed
    style completed fill:#f2f2f2,stroke:#777,stroke-width:1px
```


## 古埃及法老制 (`egypt_pipeline`)
- Default Spec: `systems/institutions/egypt_pipeline/egypt_pipeline.yaml`
- Pattern: `pipeline` | Stages: `3` | Transitions: `2` | Gates: `0` | Auditors: `0` | Feedback Loops: `0`
- Parallel Consensus Points: `none`
- Parallel Cluster Points: `none`
- Enabled Runtime Features: `monitor`
- Report-Feature Mapping: `none`

### Topology
```mermaid
flowchart LR
    vizier_planning["vizier_planning\n[planner]\n@vizier"]
    nomarch_execution["nomarch_execution\n[executor]\n@nomarch"]
    completed["completed\n[terminal]"]
    vizier_planning -- "next" --> nomarch_execution
    nomarch_execution -- "next" --> completed
    style completed fill:#f2f2f2,stroke:#777,stroke-width:1px
```
