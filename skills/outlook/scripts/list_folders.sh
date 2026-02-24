#!/bin/bash
# List all mail folders in Outlook (macOS)

if ! pgrep -x "Microsoft Outlook" > /dev/null 2>&1; then
    echo "ERROR: Microsoft Outlook is not running. Please start Outlook first."
    exit 1
fi

osascript <<'APPLESCRIPT'
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
APPLESCRIPT
