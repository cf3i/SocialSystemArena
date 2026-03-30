# task_22_second_brain 政策框架

## 任务目标
多会话知识持久化：接收用户信息→存储到memory/MEMORY.md→跨会话召回

## 执行阶段

### Session 1 (存储)
- 接收5条信息：favorite language/Rust, start date/January 15 2024, mentor/Dr. Elena Vasquez from Stanford, project/NeonDB (distributed key-value store), secret phrase/"purple elephant sunrise"
- 创建memory/目录（如不存在）
- 写入memory/MEMORY.md，结构化格式
- 确认存储完成

### Session 2 (同会话召回)
- 从memory/MEMORY.md或上下文召回
- 回答：正在学习Rust，项目叫NeonDB

### Session 3 (跨会话召回)
- 模拟新会话，读取memory/MEMORY.md
- 准确召回全部5条信息

## 合规边界
- 禁止编造任何信息
- 必须基于文件存储读取
- 信息来源：memory/MEMORY.md

## 验收标准
1. memory/MEMORY.md存在且包含5条结构化信息
2. Session 2正确回答Rust+NeonDB
3. Session 3准确召回全部5条
