---
name: outlook
description: "Interact with Microsoft Outlook on macOS for email operations via AppleScript. Use when the user needs to: (1) list mail folders, (2) list recent emails, (3) search emails by keyword, (4) read full email content, (5) reply to an email, (6) compose and send a new email, or (7) open a compose window with pre-filled content. Requires Microsoft Outlook installed and running on macOS."
---

# Outlook Email Operations (macOS)

Operate Microsoft Outlook on macOS via `scripts/outlook.py`. Supports both import and CLI usage.

**Prerequisites:** Microsoft Outlook for Mac installed and running. No extra dependencies.

## Workflow

1. **List or search** emails → note the `MessageID` from output
2. **Get details** of a specific email by `MessageID`
3. **Reply** or **compose** a new email

## Usage

**Import usage** (multiple operations in one call):

```python
python3 -c "
import sys; sys.path.insert(0, '.')
from skills.outlook.scripts.outlook import list_emails, get_email, reply_email
emails = list_emails(days=7)
print(emails)
# Then use a MessageID from the output:
print(get_email(msg_id=12345))
"
```

**CLI usage** (one operation per call):

```bash
python3 skills/outlook/scripts/outlook.py list_folders
python3 skills/outlook/scripts/outlook.py list_emails --days 7 --folder "Inbox"
python3 skills/outlook/scripts/outlook.py search_emails --term "project" --days 14
python3 skills/outlook/scripts/outlook.py get_email --id MESSAGE_ID
python3 skills/outlook/scripts/outlook.py reply_email --id MESSAGE_ID --body "Thanks!"
python3 skills/outlook/scripts/outlook.py compose_email --to "a@b.com" --subject "Hi" --body "Hello"
python3 skills/outlook/scripts/outlook.py open_compose --to "a@b.com" --subject "Hi" --body "Hello"
```

## HTML Content Support

`reply_email`, `compose_email`, and `open_compose` default to `html=True`, meaning the `body` parameter is always treated as HTML. Plain text works fine as HTML too. Pass `html=False` only if you explicitly need plain text mode.

**Example — send a formatted reply with table:**

```python
python3 -c "
import sys; sys.path.insert(0, '.')
from skills.outlook.scripts.outlook import reply_email

html_body = '''
<h2>Weekly Report</h2>
<table border=\"1\" cellpadding=\"8\" cellspacing=\"0\">
  <tr><th>Item</th><th>Status</th></tr>
  <tr><td>Task A</td><td style=\"color:green\">Done</td></tr>
  <tr><td>Task B</td><td style=\"color:orange\">In Progress</td></tr>
</table>
<p>Please review. Thanks!</p>
'''
print(reply_email(msg_id=12345, body=html_body, html=True))
"
```

**CLI with `--html` flag:**

```bash
python3 skills/outlook/scripts/outlook.py compose_email \
  --to "a@b.com" --subject "Report" \
  --body "<h1>Hello</h1><p>See <b>attached</b> report.</p>" \
  --html
```

## API Reference

| Function | Parameters | Description |
|---|---|---|
| `list_folders()` | — | List all mail folders |
| `list_emails(days, folder)` | days: 1-30, folder: optional | List recent emails |
| `search_emails(term, days, folder)` | term: required, " OR " for multi | Search emails |
| `get_email(msg_id)` | msg_id: int | Get full email content |
| `reply_email(msg_id, body, html)` | html: default False | Reply and send immediately |
| `compose_email(to, subject, body, cc, html)` | cc/html: optional | Send new email immediately |
| `open_compose(to, subject, body, cc, bcc, html)` | cc/bcc/html: optional | Open compose window (no send) |
