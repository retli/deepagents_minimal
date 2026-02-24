#!/bin/bash
# Reply to an email by message ID (macOS Outlook)
# Usage: bash reply_email.sh --id MESSAGE_ID --body "Reply text"

MSG_ID=""
BODY=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --id) MSG_ID="$2"; shift 2 ;;
        --body) BODY="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$MSG_ID" ]]; then echo "ERROR: --id is required"; exit 1; fi
if [[ -z "$BODY" ]]; then echo "ERROR: --body is required"; exit 1; fi

if ! pgrep -x "Microsoft Outlook" > /dev/null 2>&1; then
    echo "ERROR: Microsoft Outlook is not running. Please start Outlook first."
    exit 1
fi

# Escape for AppleScript
ESCAPED_BODY=$(echo "$BODY" | sed 's/\\/\\\\/g; s/"/\\"/g')

osascript <<APPLESCRIPT
tell application "Microsoft Outlook"
    set targetMsg to message id ${MSG_ID}

    if targetMsg is missing value then
        return "ERROR: Message not found."
    end if

    set replyMsg to reply to targetMsg without opening window
    set content of replyMsg to "${ESCAPED_BODY}" & return & return & content of replyMsg
    send replyMsg

    set senderName to ""
    set senderAddr to ""
    try
        set senderName to name of sender of targetMsg
        set senderAddr to address of sender of targetMsg
    end try

    return "Reply sent successfully to: " & senderName & " <" & senderAddr & ">"
end tell
APPLESCRIPT
