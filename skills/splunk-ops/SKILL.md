---
name: splunk-ops
description: Splunk 日志与知识对象操作，包括索引查询、SPL 检索、知识对象管理、KV Store 统计、用户与实例信息获取。用于“查日志/查索引/查告警/查用户/查知识对象/查实例状态”等场景。
---

# Splunk Ops（日志与知识对象操作）

## 可用工具
- `get_indexes(row_limit?)`：列出所有索引。
- `get_index_info(index_name)`：查某个索引详情。
- `run_splunk_query(query, earliest_time?, latest_time?, row_limit?)`：执行 SPL 查询。
- `get_knowledge_objects(type, row_limit?)`：查知识对象（如 saved_searches、alerts）。
- `get_kv_store_collections(row_limit?)`：查 KV Store 统计。
- `get_splunk_info()`：查实例信息。
- `get_user_info()` / `get_user_list(row_limit?)`：查当前用户与用户列表。
- `get_metadata(type, index?, earliest_time?, latest_time?, row_limit?)`：查 hosts/sources/sourcetypes 元数据。

## 执行步骤
1) 明确查询目标（索引/日志/知识对象/用户/实例/元数据）。
2) 选择对应工具并传入参数。
3) 汇总结果，引用关键字段。
4) 禁止编造，若无结果需说明。

## 输出建议
- 结论：简明描述查询结果。
- 证据：引用工具返回的关键字段。
- 建议：如有异常或风险，给出后续建议。