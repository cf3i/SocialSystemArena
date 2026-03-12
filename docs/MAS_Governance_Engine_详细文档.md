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
- `soul_file_path`（推荐，读取外部 `soul.md`）
- `prompt_template`（兼容旧写法，建议迁移）
- `default_decision`
- `transitions`

特殊字段：

- `consensus`：仅 `kind=consensus` 使用
- `cluster_members`：仅 `kind=cluster` 使用
- `sop`：可选 SOP 校验规则（`required_patterns` / `forbidden_patterns` / `on_violation`）

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

### 4.4 `sop`

用于约束阶段输出必须满足某些规则（例如必须出现某条 CLI 证据）：

- `required_patterns`：必须命中的正则数组
- `forbidden_patterns`：禁止命中的正则数组
- `on_violation`：违规处理策略，支持 `error|retry|force_decision`

### 4.5 `policy`

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

### 5.1 Prompt 组装顺序

每个 stage 的 prompt 由以下层次拼接而成（从上到下）：

1. `stage.description`（节点目标）
2. `systems/pattern_souls/<pattern>/<stage.kind>.md`（pattern 级节点职责，可选）
3. `stage.soul_file_path`（制度级节点 SOUL）

冲突优先级：

- `Stage Objective > Institution SOP > Pattern Rules`

运行时会把三层内容渲染为固定标签段：

- `[Stage Objective]`
- `[Pattern Rules]`
- `[Institution SOP]`

并对 prompt 做两种约束：

- 行级去重（减少重复规则）
- 长度裁剪（单段与整体上限）

最后统一附加 topology contract（`transitions` / `allowed_decisions` / JSON 输出 schema）。

当 `stage.soul_file_path` 未配置时，才会回退到 `prompt_template`（兼容模式）。

### 5.2 Consensus 聚合

支持算法：

- `majority`
- `weighted`
- `unanimity`

正向票集合：`approve/approved/yes/pass/accepted/success`

### 5.3 Cluster 聚合

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

当前 `systems/` 结构：

- `systems/pattern_souls/`：pattern 级通用 SOUL
- `systems/institutions/<institution_id>/`：制度 spec 与制度 SOUL

已落地制度示例：

- `systems/institutions/egypt_pipeline/egypt_pipeline.json`
- `systems/institutions/qinhan_junxian/qinhan_junxian.json`
- `systems/institutions/tang_sanshengliubu/tang_sanshengliubu.json`
- `systems/institutions/us_federal/us_federal_gated.json`
- `systems/institutions/athens_democracy/athens_consensus.json`
- `systems/institutions/egypt_pipeline/egypt_pipeline.yaml`（YAML 版本示例）

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

---

## 13. Dashboard + 后端事件流（新增）

### 13.1 设计目标

为了满足“可观测 + 可回放 + 实时态势”需求，新增了一个轻量后端：

- `TaskRunManager`：异步执行任务（后台线程）
- `InMemoryEventStream`：按 `task_id` 维护有序事件流（含 `stream_seq`）
- `EventStreamStore`：把运行时 trace 同时写入 JSONL 并发布事件
- HTTP API + SSE：前端实时订阅任务事件
- Dashboard：拓扑可视化 + 事件时间线 + agent trace 明细

### 13.2 启动方式

```bash
python -m mas_engine.cli serve \
  --host 127.0.0.1 \
  --port 8787 \
  --trace-dir traces/dashboard
```

打开：

`http://127.0.0.1:8787`

### 13.3 API 一览

- `POST /api/runs`：发起任务
- `GET /api/tasks`：任务列表
- `GET /api/tasks/{task_id}`：任务快照
- `GET /api/tasks/{task_id}/topology`：该任务拓扑
- `GET /api/tasks/{task_id}/events?since=0&limit=200`：事件回放
- `GET /api/tasks/{task_id}/stream?since=0`：SSE 实时流
- `GET /api/spec-topology?spec=systems/xxx.yaml`：预览 spec 拓扑

### 13.4 事件类型

SSE/回放输出统一携带 `stream_seq`，并按 `record_type` 区分：

- `lifecycle`
  - `task_queued`
  - `task_started`
  - `task_finished`
  - `task_error`
- `stage_event`
  - 每个 stage 一条聚合流转记录
- `agent_trace`
  - 每个 agent dispatch 一条记录，含 `sequential_id`

### 13.5 与 trace 文件关系

如果指定 `trace_out`（或使用默认 `trace_dir/TASK-xxx.jsonl`）：

- JSONL 仍按原格式落盘（可离线审计）
- 同时同内容推送到事件流（用于 dashboard 实时展示）

即：**一份事实来源，两个消费通道（离线文件 + 在线事件）**。

### 13.6 制度映射（Institution Registry）

新增 `systems/institutions.yaml` 作为制度目录层，避免前端直接暴露文件路径：

- `institution_id / institution_name / description`
- `default_spec_id`
- `specs[]`：`spec_id/spec_name/path`

典型调用：

- `GET /api/institutions`：制度列表（给下拉框）
- `GET /api/institutions/{id}`：制度详情 + spec 版本列表
- `GET /api/specs/{spec_id}`：spec 文本 + topology + spec_ir

### 13.7 Dashboard 自定义 YAML

Dashboard 支持两种来源：

1. 从制度目录加载既有 spec（最直观）  
2. 通过 Builder 生成/修改 spec（pattern + feature + stages）

Builder 生成流程：

1. 选择 `pattern`
2. 勾选 `features`
3. 添加/编辑 stage（`id/kind/agent/transitions`）
4. `Builder -> YAML`（调用 `POST /api/specs/to-yaml`）
5. `校验当前YAML`（调用 `POST /api/specs/validate`）
6. `运行当前YAML`（`POST /api/runs` with `spec_inline`）

最新 Dashboard 还支持：

- 交互式 SVG 拓扑图（节点/边/decision 标签）
- 节点-事件-trace 联动（点击任一处可聚焦 stage）
- Event/Trace 实时过滤和关键词搜索
- Stage Inspector：
  - `consensus` 的 voters/algorithm/threshold/tie_breaker
  - `cluster` 的成员列表（`agent|role|required`）

### 13.8 inline spec 运行

`POST /api/runs` 支持：

- `spec_inline + spec_format`（`yaml/json`）
- `spec_id`
- `institution_id`（自动取默认 spec）
- `spec`/`spec_path`（兼容旧方式）

优先级：`spec_obj` > `spec_inline` > `spec_id` > `institution_id` > `spec_path`。
