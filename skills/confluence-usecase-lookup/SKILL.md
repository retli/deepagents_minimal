---
name: confluence-usecase-lookup
description: 根据 UseCase ID 从 Confluence 查询用例详情（目标、分类、策略摘要、技术上下文等）。当用户要求“查某个 UseCase 详情/策略/背景/上下文”时使用。
---

# Confluence UseCase Lookup

## 可用工具（必须真实调用）
- `query_usecase(usecase_id)`：一次仅支持一个 UseCase ID。

## 执行步骤（必须遵守）
1) **校验 ID 格式**：确认符合 `(BBA|NSC|CIS|BCS|SF5)-<word>-(ATK|DLP|COMP|INFO|CUS-AID-<6chars>|AID-<5chars>)`。
2) **调用工具**：传入 `usecase_id`，单次只查一个。
3) **禁止编造**：仅基于工具返回字段输出；无结果则明确说明并提示确认 ID。

## 输出格式（建议）
- **标题**：UseCase ID + Title
- **目标**：Goal
- **分类**：Categorization
- **策略摘要**：Strategy Abstract
- **技术上下文**：Technical Context
- **其他要点**（如有）：关键字段摘要

## 例子（用户可能这样问）
- “查一下 `BBA-Project-ATK-AID-123456` 的 UseCase 详情”
- “`NSC-Test-AID-12345` 的策略摘要和技术上下文是什么？”