---
name: outlook
description: "Interact with Microsoft Outlook on macOS for email operations via AppleScript. Use when the user needs to: (1) list mail folders, (2) list recent emails, (3) search emails by keyword, (4) read full email content, (5) reply to an email, (6) compose and send a new email, or (7) open a compose window with pre-filled content. Requires Microsoft Outlook installed and running on macOS."
---

# Outlook Email Operations (macOS)

通过 `scripts/outlook.py` 操作 macOS 上的 Microsoft Outlook，所有功能通过 import 方式调用。

**前提条件：** Microsoft Outlook for Mac 已安装并正在运行。无需额外依赖。

## 调用方式

所有操作统一使用 Python import 模式，支持在一次 `run_command` 中执行多个操作：

```python
python3 -c "
import sys; sys.path.insert(0, '.')
from skills.outlook.scripts.outlook import list_emails, get_email, reply_email
print(list_emails(days=7))
print(get_email(msg_id=12345))
"
```

## 典型工作流

1. **列出或搜索**邮件 → 从输出中获取 `MessageID`
2. 通过 `MessageID` **获取**邮件详情
3. **回复**邮件 或 **撰写**新邮件

## API 参考

### `list_folders()`
列出所有邮箱账户下的所有文件夹。

```python
from skills.outlook.scripts.outlook import list_folders
print(list_folders())
```

### `list_emails(days=7, folder=None)`
列出最近 N 天的邮件。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `days` | int | 否 | 7 | 查询天数范围（1-30） |
| `folder` | str | 否 | None | 指定文件夹名，None 则使用收件箱 |

```python
from skills.outlook.scripts.outlook import list_emails
print(list_emails(days=7))
print(list_emails(days=14, folder="项目通知"))
```

### `search_emails(term, days=7, folder=None)`
按关键词搜索邮件（匹配主题、发件人、正文）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `term` | str | **是** | — | 搜索关键词，多词用 `" OR "` 连接 |
| `days` | int | 否 | 7 | 查询天数范围（1-30） |
| `folder` | str | 否 | None | 指定文件夹名 |

```python
from skills.outlook.scripts.outlook import search_emails
print(search_emails(term="报告"))
print(search_emails(term="周报 OR 日报", days=14))
```

### `get_email(msg_id)`
通过 MessageID 获取邮件完整内容。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `msg_id` | int | **是** | 从 list/search 结果中获取的 MessageID |

```python
from skills.outlook.scripts.outlook import get_email
print(get_email(msg_id=12345))
```

### `reply_email(msg_id, body, html=True)`
回复邮件并立即发送。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `msg_id` | int | **是** | — | 目标邮件的 MessageID |
| `body` | str | **是** | — | 回复内容（默认为 HTML 格式） |
| `html` | bool | 否 | True | 是否将 body 作为 HTML 处理 |

```python
from skills.outlook.scripts.outlook import reply_email
# 纯文本回复
print(reply_email(msg_id=12345, body="收到，谢谢！"))
# HTML 格式回复
print(reply_email(msg_id=12345, body="<h2>周报</h2><p>已完成全部任务。</p>"))
```

### `compose_email(to, subject, body, cc=None, html=True)`
撰写并立即发送新邮件。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `to` | str | **是** | — | 收件人邮箱 |
| `subject` | str | **是** | — | 邮件主题 |
| `body` | str | **是** | — | 邮件正文（默认 HTML） |
| `cc` | str | 否 | None | 抄送邮箱 |
| `html` | bool | 否 | True | 是否将 body 作为 HTML 处理 |

```python
from skills.outlook.scripts.outlook import compose_email
print(compose_email(to="a@b.com", subject="会议通知", body="<p>明天下午3点开会</p>"))
```

### `open_compose(to, subject, body, cc=None, bcc=None, html=True)`
打开 Outlook 撰写窗口并预填内容（**不自动发送**，用户手动确认后发送）。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `to` | str | **是** | — | 收件人邮箱 |
| `subject` | str | **是** | — | 邮件主题 |
| `body` | str | **是** | — | 邮件正文（默认 HTML） |
| `cc` | str | 否 | None | 抄送邮箱 |
| `bcc` | str | 否 | None | 密送邮箱 |
| `html` | bool | 否 | True | 是否将 body 作为 HTML 处理 |

```python
from skills.outlook.scripts.outlook import open_compose
print(open_compose(to="a@b.com", subject="确认", body="<p>请确认附件内容。</p>", cc="c@d.com"))
```

## HTML 内容支持

`reply_email`、`compose_email`、`open_compose` 默认 `html=True`，即 `body` 参数默认按 HTML 处理。纯文本内容也完全兼容（会被当作 HTML 渲染）。仅在你明确需要纯文本模式时传 `html=False`。

**示例 — 发送带表格的格式化回复：**

```python
from skills.outlook.scripts.outlook import reply_email

html_body = '''
<h2>Weekly Report</h2>
<table border="1" cellpadding="8" cellspacing="0">
  <tr><th>Item</th><th>Status</th></tr>
  <tr><td>Task A</td><td style="color:green">Done</td></tr>
  <tr><td>Task B</td><td style="color:orange">In Progress</td></tr>
</table>
<p>Please review. Thanks!</p>
'''
print(reply_email(msg_id=12345, body=html_body))
```
