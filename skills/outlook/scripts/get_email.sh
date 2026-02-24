#!/bin/bash
# Get full email details by message ID (macOS Outlook)
# Usage: bash get_email.sh --id MESSAGE_ID

MSG_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --id) MSG_ID="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$MSG_ID" ]]; then
    echo "ERROR: --id is required (use MessageID from list or search results)"
    exit 1
fi

if ! pgrep -x "Microsoft Outlook" > /dev/null 2>&1; then
    echo "ERROR: Microsoft Outlook is not running. Please start Outlook first."
    exit 1
fi

osascript <<APPLESCRIPT
tell application "Microsoft Outlook"
    set targetMsg to message id ${MSG_ID}

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

    -- To recipients
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

    -- CC recipients
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

    -- Attachments
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

    -- Body
    set msgBody to ""
    try
        set msgBody to plain text content of targetMsg
    end try
    set resultText to resultText & linefeed & "Body:" & linefeed & msgBody

    return resultText
end tell
APPLESCRIPT
