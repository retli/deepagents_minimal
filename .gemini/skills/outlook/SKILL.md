---
name: outlook
description: "Interact with Microsoft Outlook on macOS for email operations via AppleScript. Use when the user needs to: (1) list mail folders, (2) list recent emails, (3) search emails by keyword, (4) read full email content, (5) reply to an email, (6) compose and send a new email, or (7) open a compose window with pre-filled content. Requires Microsoft Outlook installed and running on macOS."
---

# Outlook Email Operations (macOS)

Operate Microsoft Outlook on macOS via shell scripts that execute AppleScript. All scripts are in `scripts/`.

**Prerequisites:** Microsoft Outlook for Mac installed and running.

## Workflow

1. **List or search** emails → note the `MessageID` from output
2. **Get details** of a specific email by `MessageID`
3. **Reply** or **compose** a new email

## Operations

### List Mail Folders

```bash
bash .gemini/skills/outlook/scripts/list_folders.sh
```

### List Recent Emails

```bash
bash .gemini/skills/outlook/scripts/list_emails.sh [--days N] [--folder NAME]
```

- `--days N` : Days to look back (1-30, default: 7)
- `--folder NAME` : Folder name (default: Inbox)

### Search Emails

```bash
bash .gemini/skills/outlook/scripts/search_emails.sh --term "keyword" [--days N] [--folder NAME]
```

- `--term TEXT` : Search keyword (required). Use `" OR "` to combine terms.
- `--days N` : Days to look back (1-30, default: 7)
- `--folder NAME` : Folder name (default: Inbox)

### Get Email Details

```bash
bash .gemini/skills/outlook/scripts/get_email.sh --id MESSAGE_ID
```

### Reply to Email

```bash
bash .gemini/skills/outlook/scripts/reply_email.sh --id MESSAGE_ID --body "Reply text"
```

⚠️ Reply is sent immediately.

### Compose and Send Email

```bash
bash .gemini/skills/outlook/scripts/compose_email.sh --to "email" --subject "subject" --body "body" [--cc "email"]
```

⚠️ Email is sent immediately.

### Open Compose Window (No Auto-Send)

```bash
bash .gemini/skills/outlook/scripts/open_compose.sh --to "email" --subject "subject" --body "body" [--cc "email"] [--bcc "email"]
```

Opens Outlook compose window with pre-filled content for manual review before sending.
