#!/bin/bash
# List recent emails from Outlook (macOS)
# Usage: bash list_emails.sh [--days N] [--folder NAME]

DAYS=7
FOLDER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --days) DAYS="$2"; shift 2 ;;
        --folder) FOLDER="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ "$DAYS" -lt 1 || "$DAYS" -gt 30 ]]; then
    echo "ERROR: days must be between 1 and 30"; exit 1
fi

if ! pgrep -x "Microsoft Outlook" > /dev/null 2>&1; then
    echo "ERROR: Microsoft Outlook is not running. Please start Outlook first."
    exit 1
fi

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

osascript <<APPLESCRIPT
-- Calculate threshold date OUTSIDE the tell block to avoid
-- Outlook hijacking the 'date' keyword
set thresholdDate to (current date) - (${DAYS} * days)

tell application "Microsoft Outlook"
    ${FOLDER_REF}

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
        return "No emails found in the last ${DAYS} days."
    end if

    return "Found " & emailCount & " emails:" & linefeed & linefeed & resultText
end tell
APPLESCRIPT
