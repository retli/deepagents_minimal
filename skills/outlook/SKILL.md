---
name: outlook
description: "Interact with Microsoft Outlook on macOS for email operations via AppleScript. Use when the user needs to: (1) list mail folders, (2) list recent emails, (3) search emails by keyword, (4) read full email content, (5) reply to an email, (6) compose and send a new email, or (7) open a compose window with pre-filled content. Requires Microsoft Outlook installed and running on macOS."
---

# Outlook Email Operations (macOS)

Operate Microsoft Outlook on macOS via shell scripts that execute AppleScript. All scripts are in the `scripts/` subdirectory relative to this SKILL.md file.

**Prerequisites:** Microsoft Outlook for Mac installed and running.

**Script Location:** All scripts are located at `skills/outlook/scripts/` relative to the project root. The scripts are self-contained with no external path dependencies — they can be invoked from any working directory using their absolute or relative path.

## Workflow

1. **List or search** emails → note the `MessageID` from output
2. **Get details** of a specific email by `MessageID`
3. **Reply** or **compose** a new email

## Operations

In the examples below, `SCRIPT_DIR` refers to the `scripts/` directory within this skill folder. Resolve it relative to the project root or this SKILL.md file. For example:

```bash
# From project root:
SCRIPT_DIR="skills/outlook/scripts"
# Or resolve dynamically from this file's location:
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)/scripts"
```

### List Mail Folders

```bash
bash "$SCRIPT_DIR/list_folders.sh"
```

### List Recent Emails

```bash
bash "$SCRIPT_DIR/list_emails.sh" [--days N] [--folder NAME]
```

- `--days N` : Days to look back (1-30, default: 7)
- `--folder NAME` : Folder name (default: Inbox)

### Search Emails

```bash
bash "$SCRIPT_DIR/search_emails.sh" --term "keyword" [--days N] [--folder NAME]
```

- `--term TEXT` : Search keyword (required). Use `" OR "` to combine terms.
- `--days N` : Days to look back (1-30, default: 7)
- `--folder NAME` : Folder name (default: Inbox)

### Get Email Details

```bash
bash "$SCRIPT_DIR/get_email.sh" --id MESSAGE_ID
```

### Reply to Email

```bash
bash "$SCRIPT_DIR/reply_email.sh" --id MESSAGE_ID --body "Reply text"
```

⚠️ Reply is sent immediately.

### Compose and Send Email

```bash
bash "$SCRIPT_DIR/compose_email.sh" --to "email" --subject "subject" --body "body" [--cc "email"]
```

⚠️ Email is sent immediately.

### Open Compose Window (No Auto-Send)

```bash
bash "$SCRIPT_DIR/open_compose.sh" --to "email" --subject "subject" --body "body" [--cc "email"] [--bcc "email"]
```

Opens Outlook compose window with pre-filled content for manual review before sending.
