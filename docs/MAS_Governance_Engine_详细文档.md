# MAS Governance Engine 详细文档

本文档面向项目维护者与制度建模者，说明当前框架的设计目标、核心抽象、运行机制、规范格式、扩展方式与落地流程。

---

## 1. 项目定位

`mas_engine` 是一个通用的多智能体治理运行框架，核心思想是：

- 用 `Pattern` 描述消息流拓扑（主流程结构）
- 用 `Feature` 描述可叠加机制（监控、护栏、应急、人类确认等）
- 用统一规范文件（JSON/CUE/YAML）描述“制度”
- 用统一运行时执行不同制度，不为每个制度重写代码

运行时核心独立于 `sample/`，并可通过 `PcAgentLoopAdapter` 对接 `third_party/pc-agent-loop` 作为执行后端。

---

## 2. 总体架构

代码结构：

- `mas_engine/spec/`：规范层（`templates/compiler/validators`）
- `mas_engine/core/`：运行时核心（`types/errors/features/runtime`）
- `mas_engine/storage/`：持久化层（`jsonl` trace 存储）
- `mas_engine/adapters/`：Agent 执行适配层（`MockAdapter`、`PcAgentLoopAdapter`、`OpenClawAdapter`）
- `mas_engine/cli.py`：命令行入口（`init-spec / validate / compile / run`）

运行数据流：

1. 读取制度规范（`*.json` / `*.yaml` / `*.cue`）
2. 编译 + 语义校验
3. 进入 runtime 主循环（`entry_stage`）
4. 每步执行：`before_stage` -> `adapter.dispatch` -> `after_stage`
5. 基于 `decision` 查找 transition，推进到下一 stage
6. 记录事件（内存 + 可选 JSONL trace）
   - `agent_trace`：每次 agent dispatch 一条，包含 `sequential_id`
   - `stage_event`：每个 stage 聚合结果一条
7. 到达 `terminal` 后完成

---

## 3. 核心抽象

### 3.1 Pattern（主拓扑）

当前支持 4 类：

- `pipeline`
- `gated_pipeline`
- `autonomous_cluster`
- `consensus`

语义约束（由 `validators.py` 强制）：

- `pipeline` 不能包含 `gate/consensus/cluster`
- `gated_pipeline` 至少包含一个 `gate`
- `autonomous_cluster` 必须包含 `orchestrator` 和 `cluster`
- `consensus` 必须包含 `consensus` stage

### 3.2 Stage（节点）

当前 stage kind：

- `initiator`
- `planner`
- `gate`
- `executor`
- `auditor`
- `orchestrator`
- `consensus`
- `cluster`
- `terminal`

每个非 terminal stage 必须定义 `transitions`。

### 3.3 Feature（可叠加能力）

当前内置插件：

- `monitor`：在事件 meta 中记录运行心跳
- `shared_state`：将 agent `updates` 合并到全局共享状态
- `system_protocol`：检测输出是否触犯禁词，强制改判
- `emergency_handler`：连续失败触发应急决策
- `human_confirmation`：关键阶段要求人工确认（HITL）

---

## 4. 规范格式（JSON/CUE/YAML）

制度文件核心字段：

- `meta`：制度元信息（id/name/version/pattern）
- `entry_stage`：入口阶段
- `agents`：角色与 runtime id 映射
- `stages`：阶段清单
- `features`：可选插件列表
- `policy`：全局策略

### 4.1 `agents`

常用字段：

- `runtime_id`：适配器层实际调用 id（后端 agent 实例标识）
- `role`：语义角色（文档化）
- `timeout_sec`：超时秒数
- `retries`：重试次数

### 4.2 `stages`

通用字段：

- `id`
- `kind`
- `agent`（`cluster/consensus` 可不填）
- `prompt_template`
- `default_decision`
- `transitions`

特殊字段：

- `consensus`：仅 `kind=consensus` 使用
- `cluster_members`：仅 `kind=cluster` 使用

### 4.3 `transitions`

格式：

```json
{"decision": "approve", "to": "next_stage_id"}
```

运行时解析顺序：

1. 精确匹配当前 decision
2. 匹配 `decision=default`
3. 若 decision 为 `next` 且 transitions 只有一条，则自动走该条
4. 否则标记运行错误

### 4.4 `policy`

- `banned_terms`：禁词
- `require_json_decision`：是否强制 agent 返回结构化 decision
- `max_steps`：最大步数上限

---

## 5. Runtime 执行细节

`GovernanceRuntime.run()` 每轮执行逻辑：

1. 读取当前 stage
2. 执行 Feature `before_stage`
3. 执行 stage：
   - 普通节点：单 agent 调用
   - `consensus`：并发发给 voter，聚合投票
   - `cluster`：并发发给成员，按 required 成员是否失败判定
4. 执行 Feature `after_stage`
5. 解析下一跳并记录 `TaskEvent`
6. 到达 `terminal` 时结束

### 5.1 Consensus 聚合

支持算法：

- `majority`
- `weighted`
- `unanimity`

正向票集合：`approve/approved/yes/pass/accepted/success`

### 5.2 Cluster 聚合

失败判定集合：`error/failed/reject/rejected/veto/cancel/cancelled`

若任一 `required=true` 成员失败，则 cluster decision = `failure`，否则 `success`。

---

## 6. Adapter 层

### 6.1 MockAdapter

用于本地调试与测试：

- 可通过 `scripted_decisions` 指定每个 agent 的决策序列
- 未指定时按简单规则返回默认 decision

### 6.2 OpenClawAdapter

通过 CLI 调用 OpenClaw：

基础命令：

```bash
openclaw agent --agent <runtime_id> -m "<message>" --timeout <sec>
```

支持 `deliver_mode`：

- `auto`：先试 `--deliver`，若 CLI 不支持则自动回退
- `always`：总是附加 `--deliver`
- `never`：从不附加 `--deliver`

并支持：

- `executable`：自定义 openclaw 可执行路径
- `project_dir`：调用时工作目录
- `extra_env`：附加环境变量

输出解析策略：

- 从 stdout/stderr 中提取最后一个包含 `decision` 的 JSON 对象
- 若无结构化 JSON，回退为 `decision=next` + 最后一行摘要

### 6.3 PcAgentLoopAdapter

通过 `third_party/pc-agent-loop` 的 `GeneraticAgent` 执行：

- `runtime_id` 默认映射到独立实例（可选共享实例）
- 调用 `put_task(...)` 投递任务，轮询 `display_queue` 等待 `done`
- 支持超时中断（调用 `abort()`）
- 输出解析策略：优先提取最后一个 `decision` JSON，失败回退为 `next`

常用参数：

- `agent_root`：`pc-agent-loop` 根目录
- `mykey_path`：显式指定 `mykey.py` / `mykey.json`
- `llm_no`：选择后端模型索引
- `shared_instance`：是否所有角色复用同一实例

---

## 7. CLI 使用

### 7.1 生成模板

```bash
python -m mas_engine.cli init-spec \
  --id my_system \
  --name "我的制度" \
  --pattern gated_pipeline \
  --out systems/my_system.json
```

### 7.2 校验规范

```bash
python -m mas_engine.cli validate --spec systems/my_system.json
```

### 7.3 编译 IR

```bash
python -m mas_engine.cli compile \
  --spec systems/my_system.json \
  --out build/my_system.ir.json
```

### 7.4 运行（Mock）

```bash
python -m mas_engine.cli run \
  --spec systems/my_system.json \
  --title "测试任务" \
  --input "请执行..." \
  --adapter mock \
  --trace-out traces/my_system.jsonl
```

### 7.5 运行（pc-agent-loop）

```bash
python -m mas_engine.cli run \
  --spec systems/my_system.json \
  --title "真实任务" \
  --input "请执行..." \
  --adapter pc-agent-loop \
  --pc-agent-root third_party/pc-agent-loop \
  --pc-mykey third_party/pc-agent-loop/mykey.py \
  --trace-out traces/live.jsonl
```

可选参数：

- `--pc-shared-instance`：所有 runtime_id 共享一个后端实例
- `--pc-llm-no`：指定 `mykey` 多后端中的索引
- `--pc-mykey`：显式指定 `mykey.py` / `mykey.json`

### 7.6 运行（OpenClaw）

```bash
python -m mas_engine.cli run \
  --spec systems/my_system.json \
  --title "真实任务" \
  --input "请执行..." \
  --adapter openclaw \
  --openclaw-bin openclaw \
  --openclaw-deliver-mode auto \
  --openclaw-project-dir /path/to/openclaw/project \
  --trace-out traces/live.jsonl
```

---

## 8. 现有制度样例

当前 `systems/` 已落地：

- `egypt_pipeline.json`
- `qinhan_junxian.json`
- `tang_sanshengliubu.json`
- `us_federal_gated.json`
- `edo_cluster.json`
- `athens_consensus.json`
- `egypt_pipeline.yaml`（YAML 版本示例）

说明：

- 唐三省六部已同时提供 `CUE + JSON`
- 秦汉郡县制是新落地样例，体现 `Pipeline + Monitor`

---

## 9. 新制度落地流程（推荐）

建议每次只落地 1 个制度，执行闭环如下：

1. 从报告中抽取制度流程与核心权力关系
2. 先判定主 Pattern（不要先写字段）
3. 映射 stage 链路与 decision 字典
4. 识别可叠加 Feature（监控/HITL/应急/护栏）
5. 生成初稿（`init-spec`）并修改为正式 spec
6. 先 `validate` 再 `run --adapter mock`
7. 为该制度新增一条测试（至少覆盖成功路径）
8. 最后做 pc-agent-loop 或 OpenClaw 联调（按部署选型）

---

## 10. 测试与质量基线

当前测试覆盖点：

- 多制度编译与约束校验
- Gated Pipeline 的拒绝-重提-通过链路
- Consensus 拒绝路径
- Pipeline 非法 gate 约束
- OpenClaw 输出解析与 `--deliver` 兼容回退
- pc-agent-loop 适配器的 JSON 解析与超时中断
- 模板生成可编译性
- CUE 编译路径稳定性
- 新制度（秦汉）运行与 monitor 元数据

运行方式：

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

---

## 11. 当前边界与后续建议

已支持：

- 统一制度建模
- 统一执行内核
- 统一适配层

尚未内建（可扩展）：

- `recursive_executor` 一等语义（当前可通过多 stage 近似）
- Planner 内部共识强/弱约束的显式建模
- Symbolic trigger / 节点生命周期控制等高级 Feature
- 更简化的“业务短格式 YAML”（当前支持的是等价结构 YAML）

推荐后续优先级：

1. 扩展 DSL 语义（尤其递归执行与内部共识）
2. 将报告中的高代表制度继续结构化落地
3. 增加 pc-agent-loop / OpenClaw 端到端集成测试

---

## 12. 常见问题（FAQ）

### Q1：为什么优先 JSON/CUE，同时支持 YAML？

JSON 结构最直接、歧义最少；CUE 约束能力更强。  
YAML 现在也已支持，适合手写配置；运行时会统一编译为同一套 IR。

### Q2：`cue` 不可用怎么办？

可以直接使用 JSON 或 YAML 规范；`.cue` 仅在作者侧建模时使用。  
安装后可直接 `validate/compile` CUE 文件。

### Q3：如何保证制度改动不破坏运行？

每新增制度必须配套至少一条测试，并纳入全量 `validate + unittest`。
