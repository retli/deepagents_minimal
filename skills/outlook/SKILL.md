---
name: outlook
description: "Interact with Microsoft Outlook on macOS for email operations via AppleScript. Use when the user needs to: (1) list mail folders, (2) list recent emails, (3) search emails by keyword, (4) read full email content, (5) reply to an email, (6) compose and send a new email, or (7) open a compose window with pre-filled content. Requires Microsoft Outlook installed and running on macOS."
---

# Outlook Email Operations (macOS)

Operate Microsoft Outlook on macOS via AppleScript. Two execution methods available:

**Prerequisites:** Microsoft Outlook for Mac installed and running. No extra dependencies.

## Workflow

1. **List or search** emails → note the `MessageID` from output
2. **Get details** of a specific email by `MessageID`
3. **Reply** or **compose** a new email

---

## Method A: Python Module (Recommended)

`scripts/outlook.py` — single file, supports both import and CLI usage.

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

### Python API Reference

| Function | Parameters | Description |
|---|---|---|
| `list_folders()` | — | List all mail folders |
| `list_emails(days, folder)` | days: 1-30, folder: optional | List recent emails |
| `search_emails(term, days, folder)` | term: required, " OR " for multi | Search emails |
| `get_email(msg_id)` | msg_id: int | Get full email content |
| `reply_email(msg_id, body)` | msg_id: int, body: str | Reply and send immediately |
| `compose_email(to, subject, body, cc)` | cc: optional | Send new email immediately |
| `open_compose(to, subject, body, cc, bcc)` | cc/bcc: optional | Open compose window (no send) |

---

## Method B: Shell Scripts

Individual scripts in `scripts/`, each performs one operation.

```bash
bash scripts/list_folders.sh
bash scripts/list_emails.sh --days 7 --folder "Inbox"
bash scripts/search_emails.sh --term "keyword" --days 14
bash scripts/get_email.sh --id MESSAGE_ID
bash scripts/reply_email.sh --id MESSAGE_ID --body "Reply text"
bash scripts/compose_email.sh --to "a@b.com" --subject "Hi" --body "Hello" [--cc "cc@b.com"]
bash scripts/open_compose.sh --to "a@b.com" --subject "Hi" --body "Hello" [--cc "cc@b.com"] [--bcc "bcc@b.com"]
```

> Note: Script paths above are relative to the `skills/outlook/` directory.
