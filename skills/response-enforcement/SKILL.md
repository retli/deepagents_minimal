---
name: response-enforcement
description: 安全处置执行（网络与云），用于在 WAF/Fortigate/Wiz 上对可观测进行封禁/解封或哈希检测/取消检测。当用户要求“封禁/解封/检测/取消检测”时使用。
---

# Response Enforcement（处置执行：WAF/Fortigate/Wiz）

## 可用工具（必须真实调用）
- `waf_prod_op(case_id, operation, entity, environment, additional_tags?, data_types?, ioc_only?, limit?, observable_ids?)`：WAF 封禁/解封。
- `fortigate_main_op(case_id, operation, entity, environment, etc, additional_tags?, data_types?, ioc_only?, limit?, observable_ids?)`：主防火墙入/出向封禁/解封。
- `wiz_op(case_id, operation, entity, environment, additional_tags?, ioc_only?, limit?, observable_ids?)`：哈希检测/取消检测。

## 执行步骤（必须遵守）
1) **明确 case_id 与操作类型**：
   - WAF/Fortigate：`block` 或 `unblock`
   - Wiz：`detect` 或 `undetect`
2) **选择目标平台**：
   - Web 侧封禁 → WAF
   - 边界入/出向 → Fortigate（必须指定 `etc=inbound|outbound`）
   - 云端哈希检测 → Wiz（仅哈希）
3) **可观测获取方式**：
   - 直接提供 `observable_ids`，或使用工具自动拉取（case_id + filters）。
4) **禁止编造**：仅基于工具返回说明结果；失败需明确原因/下一步。

## 输出格式（建议）
- **结论**：执行成功/失败 + 影响范围
- **证据**：引用工具返回的关键字段
- **后续建议**：监控/回滚/复核