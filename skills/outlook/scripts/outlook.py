#!/usr/bin/env python3
"""
Outlook Email Operations for macOS via AppleScript.

Usage:
    # As importable module (recommended for agent - single run_command, multiple ops):
    python3 -c "
    from skills.outlook.scripts.outlook import list_emails, get_email
    print(list_emails(days=7))
    print(get_email(12345))
    "

    # As CLI tool:
    python3 skills/outlook/scripts/outlook.py list_folders
    python3 skills/outlook/scripts/outlook.py list_emails --days 7 --folder Inbox
    python3 skills/outlook/scripts/outlook.py search_emails --term "project" --days 14
    python3 skills/outlook/scripts/outlook.py get_email --id 12345
    python3 skills/outlook/scripts/outlook.py reply_email --id 12345 --body "Thanks!"
    python3 skills/outlook/scripts/outlook.py compose_email --to "a@b.com" --subject "Hi" --body "Hello"
    python3 skills/outlook/scripts/outlook.py open_compose --to "a@b.com" --subject "Hi" --body "Hello"
"""

import subprocess
import sys
import argparse


def _run_applescript(script: str) -> tuple:
    """Execute AppleScript, return (success: bool, output: str)."""
    try:
        proc = subprocess.run(
            ["osascript", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        return False, (proc.stderr.strip() or proc.stdout.strip())
    except subprocess.TimeoutExpired:
        return False, "AppleScript execution timed out"
    except Exception as e:
        return False, str(e)


def _check_outlook() -> str | None:
    """Return error message if Outlook is not running, else None."""
    ok, out = _run_applescript('''
    tell application "System Events"
        return (name of processes) contains "Microsoft Outlook"
    end tell
    ''')
    if not ok or out.lower() != "true":
        return "ERROR: Microsoft Outlook is not running. Please start Outlook first."
    return None


def _escape(text: str | None) -> str:
    """Escape text for embedding in AppleScript strings."""
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _folder_ref_snippet(folder_name: str | None) -> str:
    """Return AppleScript snippet that sets `targetFolder`."""
    if not folder_name:
        return "set targetFolder to inbox"
    esc = _escape(folder_name)
    return f'''
        set targetFolder to missing value
        set allAccounts to exchange accounts & pop accounts & imap accounts
        repeat with acct in allAccounts
            set allFolders to mail folders of acct
            repeat with f in allFolders
                if name of f is "{esc}" then
                    set targetFolder to f
                    exit repeat
                end if
                try
                    set subFolders to mail folders of f
                    repeat with sf in subFolders
                        if name of sf is "{esc}" then
                            set targetFolder to sf
                            exit repeat
                        end if
                    end repeat
                end try
                if targetFolder is not missing value then exit repeat
            end repeat
            if targetFolder is not missing value then exit repeat
        end repeat
        if targetFolder is missing value then
            return "ERROR: Folder '{folder_name}' not found"
        end if'''


# ── Public API ───────────────────────────────────────────────────────

def list_folders() -> str:
    """List all mail folders across all Outlook accounts."""
    err = _check_outlook()
    if err:
        return err

    ok, out = _run_applescript('''
    tell application "Microsoft Outlook"
        set folderList to ""
        set allAccounts to exchange accounts & pop accounts & imap accounts
        repeat with acct in allAccounts
            set acctName to name of acct
            set folderList to folderList & "Account: " & acctName & linefeed
            set allFolders to mail folders of acct
            repeat with f in allFolders
                set folderList to folderList & "  - " & name of f & linefeed
                try
                    set subFolders to mail folders of f
                    repeat with sf in subFolders
                        set folderList to folderList & "    - " & name of sf & linefeed
                        try
                            set subSubFolders to mail folders of sf
                            repeat with ssf in subSubFolders
                                set folderList to folderList & "      - " & name of ssf & linefeed
                            end repeat
                        end try
                    end repeat
                end try
            end repeat
        end repeat
        return folderList
    end tell
    ''')
    return out if ok else f"ERROR: {out}"


def list_emails(days: int = 7, folder: str | None = None) -> str:
    """List recent emails from the last N days."""
    if days < 1 or days > 30:
        return "ERROR: days must be between 1 and 30"
    err = _check_outlook()
    if err:
        return err

    folder_ref = _folder_ref_snippet(folder)
    script = f'''
    -- threshold date OUTSIDE tell block (Outlook hijacks 'date' keyword)
    set thresholdDate to (current date) - ({days} * days)

    tell application "Microsoft Outlook"
        {folder_ref}

        set resultText to ""
        set emailCount to 0
        set emailMessages to messages of targetFolder

        repeat with msg in emailMessages
            try
                set msgDate to time received of msg
                if msgDate ≥ thresholdDate then
                    set emailCount to emailCount + 1
                    set msgSubject to subject of msg
                    set msgSender to ""
                    try
                        set msgSender to name of sender of msg
                    end try
                    set msgSenderEmail to ""
                    try
                        set msgSenderEmail to address of sender of msg
                    end try
                    set msgTime to msgDate as string
                    set msgHasAttach to "No"
                    try
                        if (count of attachments of msg) > 0 then set msgHasAttach to "Yes"
                    end try
                    set msgIsRead to "Unread"
                    try
                        if is read of msg then set msgIsRead to "Read"
                    end try
                    set msgId to id of msg as string

                    set resultText to resultText & "Email #" & emailCount & linefeed
                    set resultText to resultText & "  Subject: " & msgSubject & linefeed
                    set resultText to resultText & "  From: " & msgSender & " <" & msgSenderEmail & ">" & linefeed
                    set resultText to resultText & "  Received: " & msgTime & linefeed
                    set resultText to resultText & "  Status: " & msgIsRead & linefeed
                    set resultText to resultText & "  Attachments: " & msgHasAttach & linefeed
                    set resultText to resultText & "  MessageID: " & msgId & linefeed
                    set resultText to resultText & linefeed
                end if
            end try
        end repeat

        if emailCount is 0 then
            return "No emails found in the last {days} days."
        end if
        return "Found " & emailCount & " emails:" & linefeed & linefeed & resultText
    end tell
    '''
    ok, out = _run_applescript(script)
    return out if ok else f"ERROR: {out}"


def search_emails(term: str, days: int = 7, folder: str | None = None) -> str:
    """Search emails by keyword in subject, sender, or body. Use ' OR ' between terms for OR logic."""
    if not term:
        return "ERROR: search term is required"
    if days < 1 or days > 30:
        return "ERROR: days must be between 1 and 30"
    err = _check_outlook()
    if err:
        return err

    # Build AppleScript search condition
    terms = [t.strip() for t in term.split(" OR ") if t.strip()]
    parts = []
    for t in terms:
        esc = _escape(t)
        parts.append(f'(msgSubject contains "{esc}" or msgSenderName contains "{esc}" or msgBody contains "{esc}")')
    condition = " or ".join(parts)
    if not condition:
        return "ERROR: no valid search terms"

    folder_ref = _folder_ref_snippet(folder)
    script = f'''
    set thresholdDate to (current date) - ({days} * days)

    tell application "Microsoft Outlook"
        {folder_ref}

        set resultText to ""
        set emailCount to 0
        set emailMessages to messages of targetFolder

        repeat with msg in emailMessages
            try
                set msgDate to time received of msg
                if msgDate ≥ thresholdDate then
                    set msgSubject to subject of msg
                    set msgSenderName to ""
                    try
                        set msgSenderName to name of sender of msg
                    end try
                    set msgBody to ""
                    try
                        set msgBody to plain text content of msg
                    end try

                    if {condition} then
                        set emailCount to emailCount + 1
                        set msgSenderEmail to ""
                        try
                            set msgSenderEmail to address of sender of msg
                        end try
                        set msgTime to msgDate as string
                        set msgHasAttach to "No"
                        try
                            if (count of attachments of msg) > 0 then set msgHasAttach to "Yes"
                        end try
                        set msgIsRead to "Unread"
                        try
                            if is read of msg then set msgIsRead to "Read"
                        end try
                        set msgId to id of msg as string

                        set resultText to resultText & "Email #" & emailCount & linefeed
                        set resultText to resultText & "  Subject: " & msgSubject & linefeed
                        set resultText to resultText & "  From: " & msgSenderName & " <" & msgSenderEmail & ">" & linefeed
                        set resultText to resultText & "  Received: " & msgTime & linefeed
                        set resultText to resultText & "  Status: " & msgIsRead & linefeed
                        set resultText to resultText & "  Attachments: " & msgHasAttach & linefeed
                        set resultText to resultText & "  MessageID: " & msgId & linefeed
                        set resultText to resultText & linefeed
                    end if
                end if
            end try
        end repeat

        if emailCount is 0 then
            return "No emails matching '{_escape(term)}' found in the last {days} days."
        end if
        return "Found " & emailCount & " emails matching '{_escape(term)}':" & linefeed & linefeed & resultText
    end tell
    '''
    ok, out = _run_applescript(script)
    return out if ok else f"ERROR: {out}"


def get_email(msg_id: int) -> str:
    """Get full email details by message ID."""
    if not msg_id:
        return "ERROR: message ID is required"
    err = _check_outlook()
    if err:
        return err

    script = f'''
    tell application "Microsoft Outlook"
        set targetMsg to message id {msg_id}
        if targetMsg is missing value then
            return "ERROR: Message not found."
        end if

        set resultText to ""
        set resultText to resultText & "Subject: " & subject of targetMsg & linefeed

        set msgSender to ""
        set msgSenderEmail to ""
        try
            set msgSender to name of sender of targetMsg
            set msgSenderEmail to address of sender of targetMsg
        end try
        set resultText to resultText & "From: " & msgSender & " <" & msgSenderEmail & ">" & linefeed
        set resultText to resultText & "Received: " & ((time received of targetMsg) as string) & linefeed

        set recipientList to ""
        try
            repeat with r in to recipients of targetMsg
                set rAddr to ""
                try
                    set rAddr to address of email address of r
                end try
                if recipientList is "" then
                    set recipientList to name of r & " <" & rAddr & ">"
                else
                    set recipientList to recipientList & ", " & name of r & " <" & rAddr & ">"
                end if
            end repeat
        end try
        set resultText to resultText & "To: " & recipientList & linefeed

        set ccList to ""
        try
            repeat with r in cc recipients of targetMsg
                set rAddr to ""
                try
                    set rAddr to address of email address of r
                end try
                if ccList is "" then
                    set ccList to name of r & " <" & rAddr & ">"
                else
                    set ccList to ccList & ", " & name of r & " <" & rAddr & ">"
                end if
            end repeat
        end try
        if ccList is not "" then
            set resultText to resultText & "CC: " & ccList & linefeed
        end if

        try
            set attachCount to count of attachments of targetMsg
            if attachCount > 0 then
                set resultText to resultText & "Attachments (" & attachCount & "):" & linefeed
                repeat with att in attachments of targetMsg
                    set resultText to resultText & "  - " & name of att & linefeed
                end repeat
            else
                set resultText to resultText & "Attachments: None" & linefeed
            end if
        end try

        set msgBody to ""
        try
            set msgBody to plain text content of targetMsg
        end try
        set resultText to resultText & linefeed & "Body:" & linefeed & msgBody
        return resultText
    end tell
    '''
    ok, out = _run_applescript(script)
    return out if ok else f"ERROR: {out}"


def reply_email(msg_id: int, body: str, html: bool = True) -> str:
    """Reply to an email by message ID. Sends immediately.
    
    Args:
        msg_id: Message ID from list/search results.
        body: Reply content. Plain text by default, or HTML if html=True.
        html: If True, body is treated as HTML content.
    """
    if not msg_id:
        return "ERROR: message ID is required"
    if not body:
        return "ERROR: reply body is required"
    err = _check_outlook()
    if err:
        return err

    escaped_body = _escape(body)
    if html:
        set_content = f'set html content of replyMsg to "{escaped_body}"'
    else:
        set_content = f'set content of replyMsg to "{escaped_body}" & return & return & content of replyMsg'
    script = f'''
    tell application "Microsoft Outlook"
        set targetMsg to message id {msg_id}
        if targetMsg is missing value then
            return "ERROR: Message not found."
        end if

        set replyMsg to reply to targetMsg without opening window
        {set_content}
        send replyMsg

        set senderName to ""
        set senderAddr to ""
        try
            set senderName to name of sender of targetMsg
            set senderAddr to address of sender of targetMsg
        end try
        return "Reply sent successfully to: " & senderName & " <" & senderAddr & ">"
    end tell
    '''
    ok, out = _run_applescript(script)
    return out if ok else f"ERROR: {out}"


def compose_email(to: str, subject: str, body: str, cc: str | None = None, html: bool = True) -> str:
    """Compose and send a new email immediately.
    
    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email content. Plain text by default, or HTML if html=True.
        cc: Optional CC email address.
        html: If True, body is treated as HTML content.
    """
    if not to or not subject or not body:
        return "ERROR: --to, --subject, --body are all required"
    err = _check_outlook()
    if err:
        return err

    cc_part = ""
    if cc:
        cc_part = f'make new cc recipient at newMessage with properties {{email address:{{address:"{_escape(cc)}"}}}}'

    content_prop = "html content" if html else "content"
    script = f'''
    tell application "Microsoft Outlook"
        activate
        set newMessage to make new outgoing message
        set subject of newMessage to "{_escape(subject)}"
        set {content_prop} of newMessage to "{_escape(body)}"
        make new to recipient at newMessage with properties {{email address:{{address:"{_escape(to)}"}}}}
        {cc_part}
        send newMessage
    end tell
    '''
    ok, out = _run_applescript(script)
    return f"Email sent successfully to: {to}" if ok else f"ERROR: {out}"


def open_compose(to: str, subject: str, body: str, cc: str | None = None, bcc: str | None = None, html: bool = True) -> str:
    """Open Outlook compose window with pre-filled content (does NOT auto-send).
    
    Args:
        to: Recipient email address.
        subject: Email subject.
        body: Email content. Plain text by default, or HTML if html=True.
        cc: Optional CC email address.
        bcc: Optional BCC email address.
        html: If True, body is treated as HTML content.
    """
    if not to or not subject or not body:
        return "ERROR: --to, --subject, --body are all required"
    err = _check_outlook()
    if err:
        return err

    cc_part = ""
    if cc:
        cc_part = f'make new cc recipient at newMessage with properties {{email address:{{address:"{_escape(cc)}"}}}}'
    bcc_part = ""
    if bcc:
        bcc_part = f'make new bcc recipient at newMessage with properties {{email address:{{address:"{_escape(bcc)}"}}}}'

    content_prop = "html content" if html else "content"
    script = f'''
    tell application "Microsoft Outlook"
        activate
        set newMessage to make new outgoing message
        set subject of newMessage to "{_escape(subject)}"
        set {content_prop} of newMessage to "{_escape(body)}"
        make new to recipient at newMessage with properties {{email address:{{address:"{_escape(to)}"}}}}
        {cc_part}
        {bcc_part}
        open newMessage
    end tell
    '''
    ok, out = _run_applescript(script)
    return "Compose window opened with pre-filled content." if ok else f"ERROR: {out}"


# ── CLI entry point ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Outlook email operations (macOS)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list_folders")

    p = sub.add_parser("list_emails")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--folder", default=None)

    p = sub.add_parser("search_emails")
    p.add_argument("--term", required=True)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--folder", default=None)

    p = sub.add_parser("get_email")
    p.add_argument("--id", type=int, required=True, dest="msg_id")

    p = sub.add_parser("reply_email")
    p.add_argument("--id", type=int, required=True, dest="msg_id")
    p.add_argument("--body", required=True)
    p.add_argument("--html", action="store_true", help="Treat body as HTML content")

    p = sub.add_parser("compose_email")
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--cc", default=None)
    p.add_argument("--html", action="store_true", help="Treat body as HTML content")

    p = sub.add_parser("open_compose")
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--cc", default=None)
    p.add_argument("--bcc", default=None)
    p.add_argument("--html", action="store_true", help="Treat body as HTML content")

    args = parser.parse_args()
    cmd = args.command

    if cmd == "list_folders":
        print(list_folders())
    elif cmd == "list_emails":
        print(list_emails(days=args.days, folder=args.folder))
    elif cmd == "search_emails":
        print(search_emails(term=args.term, days=args.days, folder=args.folder))
    elif cmd == "get_email":
        print(get_email(msg_id=args.msg_id))
    elif cmd == "reply_email":
        print(reply_email(msg_id=args.msg_id, body=args.body, html=args.html))
    elif cmd == "compose_email":
        print(compose_email(to=args.to, subject=args.subject, body=args.body, cc=args.cc, html=args.html))
    elif cmd == "open_compose":
        print(open_compose(to=args.to, subject=args.subject, body=args.body, cc=args.cc, bcc=args.bcc, html=args.html))


if __name__ == "__main__":
    main()
