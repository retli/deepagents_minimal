---
name: thehive-case-ops
description: TheHive 案件与任务操作，包括获取案件详情、列任务、列可观测、创建手工任务、写任务日志、标记/取消 IOC。用于“查案件/查任务/查 IOC/创建任务/写日志/标记 IOC”等场景。
---

# TheHive Case Ops（案件与任务操作）

## 可用工具
- `thehive_get_case(case_id)`：查案件详情。
- `thehive_case_task_all(case_id)`：列案件所有任务。
- `thehive_list_case_observables(case_id, data_types?, ioc_only?, limit?)`：列案件可观测。
- `thehive_create_case_task_op(case_id, operation, assignee?, group?, due_date_ms?, start_date_ms?)`：创建手工处置任务。
- `thehive_update_tasklog(task_id, message)`：写任务日志。
- `thehive_create_ioc(case_id, data_types?, ioc?, ioc_only?, limit?, observable_ids?)`：标记/取消 IOC。

## 执行步骤
1) 明确案件 ID 与操作目标。
2) 选择对应工具并传参。
3) 汇总结果，引用关键字段。
4) 禁止编造，若无结果需说明。

## 输出建议
- 结论：简明描述操作结果。
- 证据：引用工具返回的关键字段。