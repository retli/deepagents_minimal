#!/bin/bash
# Compose and send a new email via Outlook (macOS)
# Usage: bash compose_email.sh --to "email" --subject "subject" --body "body" [--cc "email"]

TO=""
SUBJECT=""
BODY=""
CC=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --to) TO="$2"; shift 2 ;;
        --subject) SUBJECT="$2"; shift 2 ;;
        --body) BODY="$2"; shift 2 ;;
        --cc) CC="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$TO" ]]; then echo "ERROR: --to is required"; exit 1; fi
if [[ -z "$SUBJECT" ]]; then echo "ERROR: --subject is required"; exit 1; fi
if [[ -z "$BODY" ]]; then echo "ERROR: --body is required"; exit 1; fi

if ! pgrep -x "Microsoft Outlook" > /dev/null 2>&1; then
    echo "ERROR: Microsoft Outlook is not running. Please start Outlook first."
    exit 1
fi

ESC_SUBJECT=$(echo "$SUBJECT" | sed 's/\\/\\\\/g; s/"/\\"/g')
ESC_BODY=$(echo "$BODY" | sed 's/\\/\\\\/g; s/"/\\"/g')
ESC_TO=$(echo "$TO" | sed 's/\\/\\\\/g; s/"/\\"/g')

CC_PART=""
if [[ -n "$CC" ]]; then
    ESC_CC=$(echo "$CC" | sed 's/\\/\\\\/g; s/"/\\"/g')
    CC_PART="make new cc recipient at newMessage with properties {email address:{address:\"${ESC_CC}\"}}"
fi

osascript <<APPLESCRIPT
tell application "Microsoft Outlook"
    activate
    set newMessage to make new outgoing message
    set subject of newMessage to "${ESC_SUBJECT}"
    set content of newMessage to "${ESC_BODY}"
    make new to recipient at newMessage with properties {email address:{address:"${ESC_TO}"}}
    ${CC_PART}
    send newMessage
end tell
APPLESCRIPT

if [[ $? -eq 0 ]]; then
    echo "Email sent successfully to: ${TO}"
else
    echo "ERROR: Failed to send email"
    exit 1
fi
