#!/bin/bash
# Search emails in Outlook by keyword (macOS)
# Usage: bash search_emails.sh --term "keyword" [--days N] [--folder NAME]
# Supports OR logic: --term "meeting OR discussion"

TERM=""
DAYS=7
FOLDER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --term) TERM="$2"; shift 2 ;;
        --days) DAYS="$2"; shift 2 ;;
        --folder) FOLDER="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$TERM" ]]; then echo "ERROR: --term is required"; exit 1; fi
if [[ "$DAYS" -lt 1 || "$DAYS" -gt 30 ]]; then echo "ERROR: days must be between 1 and 30"; exit 1; fi

if ! pgrep -x "Microsoft Outlook" > /dev/null 2>&1; then
    echo "ERROR: Microsoft Outlook is not running. Please start Outlook first."
    exit 1
fi

THRESHOLD_DATE=$(date -v-"${DAYS}"d +"%Y-%m-%d")

if [[ -n "$FOLDER" ]]; then
    FOLDER_REF="
                set targetFolder to missing value
                set allAccounts to exchange accounts & pop accounts & imap accounts
                repeat with acct in allAccounts
                    set allFolders to mail folders of acct
                    repeat with f in allFolders
                        if name of f is \"${FOLDER}\" then
                            set targetFolder to f
                            exit repeat
                        end if
                        try
                            set subFolders to mail folders of f
                            repeat with sf in subFolders
                                if name of sf is \"${FOLDER}\" then
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
                    return \"ERROR: Folder '${FOLDER}' not found\"
                end if"
else
    FOLDER_REF='set targetFolder to inbox'
fi

# Parse OR terms into AppleScript condition
# IFS on " OR " is tricky; use sed to split
CONDITION=""
IFS=$'\n' read -d '' -ra TERMS < <(echo "$TERM" | sed 's/ OR /\n/g' && printf '\0')
for t in "${TERMS[@]}"; do
    t=$(echo "$t" | xargs)  # trim
    if [[ -z "$t" ]]; then continue; fi
    PART="(msgSubject contains \"${t}\" or msgSenderName contains \"${t}\" or msgBody contains \"${t}\")"
    if [[ -z "$CONDITION" ]]; then
        CONDITION="$PART"
    else
        CONDITION="${CONDITION} or ${PART}"
    fi
done

if [[ -z "$CONDITION" ]]; then echo "ERROR: No valid search terms"; exit 1; fi

osascript <<APPLESCRIPT
tell application "Microsoft Outlook"
    ${FOLDER_REF}

    set thresholdDate to date "${THRESHOLD_DATE}"
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

                if ${CONDITION} then
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
        return "No emails matching '${TERM}' found in the last ${DAYS} days."
    end if

    return "Found " & emailCount & " emails matching '${TERM}':" & linefeed & linefeed & resultText
end tell
APPLESCRIPT
