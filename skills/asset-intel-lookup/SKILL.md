---
name: asset-intel-lookup
description: 资产归属与 IOC 情报联合查询，用于根据内网/私网 IP、域名、用户名、设备名或 SN 查资产归属，并对 IP/域名/URL/哈希/邮箱做信誉与上下文情报分析。当用户需要“资产是谁/设备是谁/是否恶意/风险多高/关联情报”时使用。
---

# Asset & Threat Intel Lookup（资产归属 + 威胁情报）

## 可用工具（必须真实调用）
- `query_asset_info(domainOrip)`：支持单个或多个（逗号分隔）的域名/IP。
- `query_device_info(user_name?, device_name?, sn?)`：三选一，只能提供其中一个参数。
- `query_ioc_reputation(ioc)`：**单次只支持一个 IOC**；用于信誉/风险判断。
- `query_ioc_intelligence(ioc)`：**单次只支持一个 IOC**；用于上下文情报（campaign/actor/malware/关系图等）。

## 执行步骤（必须遵守）
1) **识别输入类型**：域名/IP？或 user_name/device_name/SN？还是 IOC 信誉/情报查询？
2) **调用正确工具**：
   - 域名/IP → `query_asset_info`（多个用逗号拼接一次调用）。
   - user_name/device_name/SN → `query_device_info`（每次只传一个参数）。
   - 信誉/风险 → `query_ioc_reputation`（每个 IOC 单独调用）。
   - 详细情报/上下文 → `query_ioc_intelligence`（每个 IOC 单独调用）。
3) **处理多目标**：多 IOC 逐个调用后汇总，逐行给出结论。
4) **禁止编造**：仅基于工具返回字段下结论；无数据需说明并提示补充输入。

## 输出格式（建议）
- **结论**：资产归属/风险等级（高/中/低/未知）+ 一句理由
- **证据**：引用工具返回关键字段（如 severity/score/labels/judgment/meta.status 等）
- **建议动作**（可选）：封禁/加白/进一步溯源/查询日志等

## 例子（用户可能这样问）
- “`10.0.0.2` 归属哪个部门？负责人是谁？”
- “`u0012345` 的电脑信息是什么？”
- “`example.com` 是否恶意？给详细情报”