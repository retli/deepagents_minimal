import datetime
import os
import subprocess
import json
import shlex
from typing import List, Optional, Dict, Any
from fastmcp import FastMCP
import logging
 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
 
# Initialize FastMCP server
mcp = FastMCP("outlook-assistant")
 
# Constants
MAX_DAYS = 30
FIELD_DELIMITER = "||~~||"  # Delimiter for fields within a single email record
RECORD_DELIMITER = "<<~~>>"  # Delimiter between email records

# Email cache for storing retrieved emails by number
email_cache = {}
 
# Helper functions
def run_applescript(script: str) -> tuple[bool, str]:
    """Execute AppleScript and return success status and output"""
    try:
        process = subprocess.Popen(
            ['osascript', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=script, timeout=60)
        
        if process.returncode == 0:
            return True, stdout.strip()
        else:
            return False, stderr.strip() if stderr else stdout.strip()
    except subprocess.TimeoutExpired:
        process.kill()
        return False, "AppleScript execution timed out"
    except Exception as e:
        return False, str(e)
 
def check_outlook_running() -> bool:
    """Check if Microsoft Outlook is running"""
    script = '''
    tell application "System Events"
        return (name of processes) contains "Microsoft Outlook"
    end tell
    '''
    success, output = run_applescript(script)
    return success and output.lower() == "true"

def ensure_outlook_running() -> tuple[bool, str]:
    """Ensure Outlook is running, return (success, error_message)"""
    if not check_outlook_running():
        return False, "Microsoft Outlook is not running. Please start Outlook first."
    return True, ""

def escape_applescript(text: str) -> str:
    """Escape special characters for AppleScript string"""
    if text is None:
        return ""
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    text = text.replace('\t', '\\t')
    return text
 
def clear_email_cache():
    """Clear the email cache"""
    global email_cache
    email_cache = {}

def parse_email_records(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parse the raw AppleScript output into a list of email dictionaries.
    Expected fields per record (separated by FIELD_DELIMITER):
      subject, sender_name, sender_email, received_time, has_attachments, is_read, message_id
    """
    emails = []
    if not raw_output or raw_output.strip() == "":
        return emails
    
    records = raw_output.split(RECORD_DELIMITER)
    for record in records:
        record = record.strip()
        if not record:
            continue
        fields = record.split(FIELD_DELIMITER)
        if len(fields) < 7:
            logger.warning(f"Skipping malformed email record (expected 7 fields, got {len(fields)}): {record[:100]}")
            continue
        
        email_data = {
            "subject": fields[0].strip(),
            "sender": fields[1].strip(),
            "sender_email": fields[2].strip(),
            "received_time": fields[3].strip(),
            "has_attachments": fields[4].strip().lower() == "true",
            "unread": fields[5].strip().lower() != "true",  # is_read -> unread (inverted)
            "message_id": fields[6].strip(),
        }
        emails.append(email_data)
    
    return emails


# MCP Tools
@mcp.tool()
def list_folders() -> str:
    """
    List all available mail folders in Outlook
    
    This MCP tool browses the folder structure in Outlook, including system folders like
    Inbox, Sent Items, Drafts, as well as user-defined folders and subfolders (up to 3 levels).
    
    Returns:
        str: Formatted folder list containing:
            - Root folder names (account names)
            - Subfolders (indented)
            - Sub-subfolders (indented)
            
            Returns error message if operation fails.
    
    Examples:
        - Basic usage: list_folders()
    
    Note:
        - Requires Outlook application installed and running on macOS
        - Returned folder names can be used in other email operation tools
    """
    logger.info("list_folders called")
    try:
        ok, err = ensure_outlook_running()
        if not ok:
            return f"Error: {err}"
        
        script = '''
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
        '''
        
        success, output = run_applescript(script)
        
        if success:
            if not output.strip():
                return "No mail folders found. Make sure Outlook has at least one configured account."
            return f"Available mail folders:\n\n{output}"
        else:
            return f"Error listing mail folders: {output}"
    except Exception as e:
        return f"Error listing mail folders: {str(e)}"
 
@mcp.tool()
def list_recent_emails(days: int = 7, folder_name: Optional[str] = None) -> str:
    """
    List recent emails from specified number of days    
    Args:
        days (int, optional): Number of days to look back. Range 1-30, default is 7.
        folder_name (str, optional): Name of folder to check. Defaults to Inbox.
                                    Supports system folders and custom folders.
    
    Returns:
        str: Formatted email list, each email contains:
            - Email number (for subsequent operations)
            - Subject, sender, received time
            - Read status, attachment info
            
            Returns appropriate message if no emails found or operation fails.
    
    Examples:
        - Last 7 days: list_recent_emails(days=7)
        - Specific folder: list_recent_emails(days=14, folder_name="Work")
        - Last day: list_recent_emails(days=1)
    
    Note:
        - Email numbers are only valid in current session
        - Calling this tool clears previous email cache
        - Use get_email_by_number to view full content
    """
    if not isinstance(days, int) or days < 1 or days > MAX_DAYS:
        return f"Error: 'days' must be an integer between 1 and {MAX_DAYS}"
    
    logger.info(f"list_recent_emails called with days={days}, folder_name={folder_name}")
    
    try:
        ok, err = ensure_outlook_running()
        if not ok:
            return f"Error: {err}"
        
        # Calculate threshold date
        threshold = datetime.datetime.now() - datetime.timedelta(days=days)
        threshold_str = threshold.strftime("%Y-%m-%d")
        
        # Build folder reference in AppleScript
        if folder_name:
            escaped_folder = escape_applescript(folder_name)
            # Try to find the folder by name across all accounts
            folder_ref = f'''
                set targetFolder to missing value
                set allAccounts to exchange accounts & pop accounts & imap accounts
                repeat with acct in allAccounts
                    set allFolders to mail folders of acct
                    repeat with f in allFolders
                        if name of f is "{escaped_folder}" then
                            set targetFolder to f
                            exit repeat
                        end if
                        try
                            set subFolders to mail folders of f
                            repeat with sf in subFolders
                                if name of sf is "{escaped_folder}" then
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
                    return "FOLDER_NOT_FOUND"
                end if
            '''
        else:
            folder_ref = 'set targetFolder to inbox'
        
        fd = FIELD_DELIMITER
        rd = RECORD_DELIMITER
        
        script = f'''
        tell application "Microsoft Outlook"
            {folder_ref}
            
            set thresholdDate to date "{threshold_str}"
            set resultText to ""
            set emailMessages to messages of targetFolder
            
            repeat with msg in emailMessages
                try
                    set msgDate to time received of msg
                    if msgDate < thresholdDate then
                        -- Messages are not guaranteed to be sorted, so we continue
                        -- but we could also exit repeat if sorted desc
                    else
                        set msgSubject to subject of msg
                        set msgSender to ""
                        try
                            set senderObj to sender of msg
                            set msgSender to name of senderObj
                        end try
                        set msgSenderEmail to ""
                        try
                            set senderObj to sender of msg
                            set msgSenderEmail to address of senderObj
                        end try
                        set msgTime to msgDate as string
                        set msgHasAttach to "false"
                        try
                            if (count of attachments of msg) > 0 then
                                set msgHasAttach to "true"
                            end if
                        end try
                        set msgIsRead to "false"
                        try
                            set msgIsRead to (is read of msg) as string
                        end try
                        set msgId to id of msg as string
                        
                        set emailRecord to msgSubject & "{fd}" & msgSender & "{fd}" & msgSenderEmail & "{fd}" & msgTime & "{fd}" & msgHasAttach & "{fd}" & msgIsRead & "{fd}" & msgId
                        
                        if resultText is "" then
                            set resultText to emailRecord
                        else
                            set resultText to resultText & "{rd}" & emailRecord
                        end if
                    end if
                end try
            end repeat
            
            return resultText
        end tell
        '''
        
        success, output = run_applescript(script)
        
        if not success:
            return f"Error retrieving emails: {output}"
        
        if output == "FOLDER_NOT_FOUND":
            return f"Error: Folder '{folder_name}' not found"
        
        # Clear previous cache
        clear_email_cache()
        
        # Parse results
        emails = parse_email_records(output)
        
        folder_display = f"'{folder_name}'" if folder_name else "Inbox"
        if not emails:
            return f"No emails found in {folder_display} from the last {days} days."
        
        result = f"Found {len(emails)} emails in {folder_display} from the last {days} days:\n\n"
        
        for i, email in enumerate(emails, 1):
            email_cache[i] = email
            
            result += f"Email #{i}\n"
            result += f"Subject: {email['subject']}\n"
            result += f"From: {email['sender']} <{email['sender_email']}>\n"
            result += f"Received: {email['received_time']}\n"
            result += f"Read Status: {'Read' if not email['unread'] else 'Unread'}\n"
            result += f"Has Attachments: {'Yes' if email['has_attachments'] else 'No'}\n\n"
        
        result += "To view the full content of an email, use the get_email_by_number tool with the email number."
        return result
    
    except Exception as e:
        return f"Error retrieving email titles: {str(e)}"
 
@mcp.tool()
def search_emails(search_term: str, days: int = 7, folder_name: Optional[str] = None) -> str:
    """
    Search emails within specified time range. Searches for emails containing specific keywords
    or contacts in Outlook folders. Supports searching in subject, sender name, and body.
    Supports OR logic (separate keywords with " OR ").
    Search results are cached and can be accessed by number for subsequent operations.
    
    Args:
        search_term (str): Keyword or contact name to search for.
                          Supports:
                          - Single keyword: "report"
                          - Contact name: "John Smith"
                          - OR logic: "report OR summary"
        days (int, optional): Number of days to look back. Range 1-30, default is 7.
        folder_name (str, optional): Name of folder to search. Defaults to Inbox.
    
    Returns:
        str: Formatted list of matching emails containing:
            - Email number (for subsequent operations)
            - Subject, sender, received time
            - Read status, attachment info
            
            Returns appropriate message if no matching emails found or operation fails.
    
    Examples:
        - Search keyword: search_emails(search_term="project", days=7)
        - Search contact: search_emails(search_term="John", days=14)
        - OR logic search: search_emails(search_term="meeting OR discussion", days=3)
        - Specific folder: search_emails(search_term="invoice", folder_name="Finance", days=30)
    
    Note:
        - Search is case-insensitive
        - Calling this tool clears previous email cache
        - Search may take time depending on email volume
    """
    if not search_term:
        return "Error: Please provide a search term"
        
    if not isinstance(days, int) or days < 1 or days > MAX_DAYS:
        return f"Error: 'days' must be an integer between 1 and {MAX_DAYS}"
    
    logger.info(f"search_emails called with search_term={search_term}, days={days}, folder_name={folder_name}")
    
    try:
        ok, err = ensure_outlook_running()
        if not ok:
            return f"Error: {err}"
        
        threshold = datetime.datetime.now() - datetime.timedelta(days=days)
        threshold_str = threshold.strftime("%Y-%m-%d")
        
        # Build folder reference
        if folder_name:
            escaped_folder = escape_applescript(folder_name)
            folder_ref = f'''
                set targetFolder to missing value
                set allAccounts to exchange accounts & pop accounts & imap accounts
                repeat with acct in allAccounts
                    set allFolders to mail folders of acct
                    repeat with f in allFolders
                        if name of f is "{escaped_folder}" then
                            set targetFolder to f
                            exit repeat
                        end if
                        try
                            set subFolders to mail folders of f
                            repeat with sf in subFolders
                                if name of sf is "{escaped_folder}" then
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
                    return "FOLDER_NOT_FOUND"
                end if
            '''
        else:
            folder_ref = 'set targetFolder to inbox'
        
        # Build search terms for OR logic
        search_terms = [term.strip() for term in search_term.split(" OR ")]
        
        # Build AppleScript search condition
        # We do case-insensitive comparison in AppleScript
        search_conditions = []
        for term in search_terms:
            escaped_term = escape_applescript(term.lower())
            # Check subject, sender name and plain text content
            condition = f'''(msgSubjectLower contains "{escaped_term}" or msgSenderLower contains "{escaped_term}" or msgBodyLower contains "{escaped_term}")'''
            search_conditions.append(condition)
        
        combined_condition = " or ".join(search_conditions)
        
        fd = FIELD_DELIMITER
        rd = RECORD_DELIMITER

        script = f'''
        tell application "Microsoft Outlook"
            {folder_ref}
            
            set thresholdDate to date "{threshold_str}"
            set resultText to ""
            set emailMessages to messages of targetFolder
            
            repeat with msg in emailMessages
                try
                    set msgDate to time received of msg
                    if msgDate ≥ thresholdDate then
                        set msgSubject to subject of msg
                        set msgSubjectLower to msgSubject as string
                        -- AppleScript 'contains' is case-insensitive by default
                        set msgSender to ""
                        try
                            set senderObj to sender of msg
                            set msgSender to name of senderObj
                        end try
                        set msgSenderLower to msgSender
                        set msgBody to ""
                        try
                            set msgBody to plain text content of msg
                        end try
                        set msgBodyLower to msgBody
                        
                        -- Check search condition
                        if {combined_condition} then
                            set msgSenderEmail to ""
                            try
                                set senderObj to sender of msg
                                set msgSenderEmail to address of senderObj
                            end try
                            set msgTime to msgDate as string
                            set msgHasAttach to "false"
                            try
                                if (count of attachments of msg) > 0 then
                                    set msgHasAttach to "true"
                                end if
                            end try
                            set msgIsRead to "false"
                            try
                                set msgIsRead to (is read of msg) as string
                            end try
                            set msgId to id of msg as string
                            
                            set emailRecord to msgSubject & "{fd}" & msgSender & "{fd}" & msgSenderEmail & "{fd}" & msgTime & "{fd}" & msgHasAttach & "{fd}" & msgIsRead & "{fd}" & msgId
                            
                            if resultText is "" then
                                set resultText to emailRecord
                            else
                                set resultText to resultText & "{rd}" & emailRecord
                            end if
                        end if
                    end if
                end try
            end repeat
            
            return resultText
        end tell
        '''
        
        success, output = run_applescript(script)
        
        if not success:
            return f"Error searching emails: {output}"
        
        if output == "FOLDER_NOT_FOUND":
            return f"Error: Folder '{folder_name}' not found"
        
        # Clear previous cache
        clear_email_cache()
        
        # Parse results
        emails = parse_email_records(output)
        
        folder_display = f"'{folder_name}'" if folder_name else "Inbox"
        if not emails:
            return f"No emails matching '{search_term}' found in {folder_display} from the last {days} days."
        
        result = f"Found {len(emails)} emails matching '{search_term}' in {folder_display} from the last {days} days:\n\n"
        
        for i, email in enumerate(emails, 1):
            email_cache[i] = email
            
            result += f"Email #{i}\n"
            result += f"Subject: {email['subject']}\n"
            result += f"From: {email['sender']} <{email['sender_email']}>\n"
            result += f"Received: {email['received_time']}\n"
            result += f"Read Status: {'Read' if not email['unread'] else 'Unread'}\n"
            result += f"Has Attachments: {'Yes' if email['has_attachments'] else 'No'}\n\n"
        
        result += "To view the full content of an email, use the get_email_by_number tool with the email number."
        return result
    
    except Exception as e:
        return f"Error searching emails: {str(e)}"
 
@mcp.tool()
def get_email_by_number(email_number: int) -> str:
    """
    Get full content of email by number
    
    This MCP tool retrieves complete email details by email number, including body and attachment list.
    Email number comes from list_recent_emails or search_emails results.
    
    Args:
        email_number (int): Email number from listing or search results.
    
    Returns:
        str: Complete email details containing:
            - Subject, sender, recipients
            - Received time
            - Attachment list (if any)
            - Full body content
            
            Returns error message if number is invalid or operation fails.
    
    Examples:
        - View email #1: get_email_by_number(email_number=1)
        - View email #5: get_email_by_number(email_number=5)
    
    Note:
        - Must call list_recent_emails or search_emails first
        - Email numbers are only valid in current session
        - Can use reply_to_email_by_number to reply to this email
    """
    try:
        if not email_cache:
            return "Error: No emails have been listed yet. Please use list_recent_emails or search_emails first."
        
        if email_number not in email_cache:
            return f"Error: Email #{email_number} not found in the current listing."
        
        email_data = email_cache[email_number]
        msg_id = email_data.get("message_id", "")
        
        if not msg_id:
            return f"Error: Email #{email_number} does not have a valid message ID."

        ok, err = ensure_outlook_running()
        if not ok:
            return f"Error: {err}"
        
        fd = FIELD_DELIMITER
        
        # Retrieve full email details via AppleScript using the message ID
        script = f'''
        tell application "Microsoft Outlook"
            set targetMsg to missing value
            -- Search for message by id
            set targetMsg to message id {msg_id}
            
            if targetMsg is missing value then
                return "MESSAGE_NOT_FOUND"
            end if
            
            set msgSubject to subject of targetMsg
            set msgSender to ""
            try
                set senderObj to sender of targetMsg
                set msgSender to name of senderObj
            end try
            set msgSenderEmail to ""
            try
                set senderObj to sender of targetMsg
                set msgSenderEmail to address of senderObj
            end try
            set msgTime to (time received of targetMsg) as string
            
            -- Get recipients
            set recipientList to ""
            try
                set toRecipients to to recipients of targetMsg
                repeat with r in toRecipients
                    set rName to name of r
                    set rAddr to ""
                    try
                        set rAddr to address of email address of r
                    end try
                    if recipientList is "" then
                        set recipientList to rName & " <" & rAddr & ">"
                    else
                        set recipientList to recipientList & ", " & rName & " <" & rAddr & ">"
                    end if
                end repeat
            end try
            
            -- Get CC recipients
            set ccList to ""
            try
                set ccRecipients to cc recipients of targetMsg
                repeat with r in ccRecipients
                    set rName to name of r
                    set rAddr to ""
                    try
                        set rAddr to address of email address of r
                    end try
                    if ccList is "" then
                        set ccList to rName & " <" & rAddr & ">"
                    else
                        set ccList to ccList & ", " & rName & " <" & rAddr & ">"
                    end if
                end repeat
            end try
            
            -- Get attachments
            set attachList to ""
            try
                set msgAttachments to attachments of targetMsg
                repeat with att in msgAttachments
                    set attName to name of att
                    if attachList is "" then
                        set attachList to attName
                    else
                        set attachList to attachList & "{fd}" & attName
                    end if
                end repeat
            end try
            
            -- Get body content
            set msgBody to ""
            try
                set msgBody to plain text content of targetMsg
            end try
            
            -- Build result
            set resultText to msgSubject & "{fd}" & msgSender & "{fd}" & msgSenderEmail & "{fd}" & msgTime & "{fd}" & recipientList & "{fd}" & ccList & "{fd}" & attachList & "{fd}" & msgBody
            return resultText
        end tell
        '''
        
        success, output = run_applescript(script)
        
        if not success:
            return f"Error retrieving email details: {output}"
        
        if output == "MESSAGE_NOT_FOUND":
            return f"Error: Email #{email_number} could not be retrieved from Outlook."
        
        # Parse the detailed email output
        fields = output.split(FIELD_DELIMITER)
        if len(fields) < 8:
            # Fallback: show cached data + note about body retrieval failure
            result = f"Email #{email_number} Details:\n\n"
            result += f"Subject: {email_data['subject']}\n"
            result += f"From: {email_data['sender']} <{email_data['sender_email']}>\n"
            result += f"Received: {email_data['received_time']}\n"
            result += f"\n(Could not retrieve full email details. Raw output: {output[:500]})\n"
            return result
        
        subject = fields[0].strip()
        sender_name = fields[1].strip()
        sender_email = fields[2].strip()
        received_time = fields[3].strip()
        recipients = fields[4].strip()
        cc_recipients = fields[5].strip()
        attachments_raw = fields[6].strip()
        # Body may contain delimiters, so join the rest
        body = FIELD_DELIMITER.join(fields[7:]).strip()
        
        result = f"Email #{email_number} Details:\n\n"
        result += f"Subject: {subject}\n"
        result += f"From: {sender_name} <{sender_email}>\n"
        result += f"Received: {received_time}\n"
        result += f"To: {recipients}\n"
        if cc_recipients:
            result += f"CC: {cc_recipients}\n"
        
        if attachments_raw:
            attachment_names = attachments_raw.split(FIELD_DELIMITER)
            result += f"Attachments ({len(attachment_names)}):\n"
            for att_name in attachment_names:
                result += f"  - {att_name.strip()}\n"
        else:
            result += "Has Attachments: No\n"
        
        result += f"\nBody:\n{body}\n"
        result += "\nTo reply to this email, use the reply_to_email_by_number tool with this email number."
        
        return result
    
    except Exception as e:
        return f"Error retrieving email details: {str(e)}"
 
@mcp.tool()
def reply_to_email_by_number(email_number: int, reply_text: str) -> str:
    """
    Reply to email by number
    
    This MCP tool quickly replies to an email by its number. Reply is automatically sent to original sender
    with quoted original message. Email number comes from list_recent_emails or search_emails results.
    
    Args:
        email_number (int): Email number from listing or search results.
        reply_text (str): Reply content. Supports multi-line text.
    
    Returns:
        str: Operation status:
            - Success: Shows recipient information
            - Failure: Shows error reason
    
    Examples:
        - Simple reply: reply_to_email_by_number(email_number=1, reply_text="Received, thanks!")
        - Multi-line reply: reply_to_email_by_number(email_number=2, reply_text="Hello,\\n\\nI have reviewed...")
    
    Note:
        - Must call list_recent_emails or search_emails first
        - Email is sent immediately and cannot be recalled
        - Reply automatically includes Outlook default signature
    """
    try:
        if not email_cache:
            return "Error: No emails have been listed yet. Please use list_recent_emails or search_emails first."
        
        if email_number not in email_cache:
            return f"Error: Email #{email_number} not found in the current listing."
        
        email_data = email_cache[email_number]
        msg_id = email_data.get("message_id", "")
        
        if not msg_id:
            return f"Error: Email #{email_number} does not have a valid message ID."
        
        ok, err = ensure_outlook_running()
        if not ok:
            return f"Error: {err}"
        
        escaped_reply = escape_applescript(reply_text)
        
        script = f'''
        tell application "Microsoft Outlook"
            set targetMsg to message id {msg_id}
            
            if targetMsg is missing value then
                return "MESSAGE_NOT_FOUND"
            end if
            
            set replyMsg to reply to targetMsg without opening window
            set content of replyMsg to "{escaped_reply}" & return & return & content of replyMsg
            send replyMsg
            
            -- Get sender info for confirmation
            set senderName to ""
            set senderAddr to ""
            try
                set senderObj to sender of targetMsg
                set senderName to name of senderObj
                set senderAddr to address of senderObj
            end try
            
            return "SUCCESS:" & senderName & " <" & senderAddr & ">"
        end tell
        '''
        
        success, output = run_applescript(script)
        
        if not success:
            return f"Error replying to email: {output}"
        
        if output == "MESSAGE_NOT_FOUND":
            return f"Error: Email #{email_number} could not be retrieved from Outlook."
        
        if output.startswith("SUCCESS:"):
            recipient_info = output[len("SUCCESS:"):].strip()
            return f"Reply sent successfully to: {recipient_info}"
        
        return f"Reply operation completed. Output: {output}"
    
    except Exception as e:
        return f"Error replying to email: {str(e)}"
 
@mcp.tool()
def compose_email(recipient_email: str, subject: str, body: str, cc_email: Optional[str] = None) -> str:
    """
    Compose and send new email
    
    This MCP tool creates and immediately sends a new email. Supports setting recipient, subject, body, and CC.
    Email is sent through Outlook default account with default signature.
    
    Args:
        recipient_email (str): Recipient email address.
        subject (str): Email subject.
        body (str): Email body content. Supports multi-line text.
        cc_email (str, optional): CC email address. Defaults to None.
    
    Returns:
        str: Operation status:
            - Success: Shows recipient information
            - Failure: Shows error reason
    
    Examples:
        - Basic email: compose_email(recipient_email="user@example.com", subject="Greeting", body="Hello!")
        - With CC: compose_email(recipient_email="user@example.com", subject="Notice", body="Content", cc_email="cc@example.com")
    
    Note:
        - Email is sent immediately and cannot be recalled
        - Use open_compose_window if editing before sending is needed
        - Automatically includes Outlook default signature
        - Requires Microsoft Outlook to be installed and running on macOS
    """
    try:
        ok, err = ensure_outlook_running()
        if not ok:
            return f"Error: {err}"
        
        escaped_subject = escape_applescript(subject)
        escaped_body = escape_applescript(body)
        escaped_recipient = escape_applescript(recipient_email)
        
        script_parts = [
            'tell application "Microsoft Outlook"',
            '    activate',
            '    set newMessage to make new outgoing message',
            f'    set subject of newMessage to "{escaped_subject}"',
            f'    set content of newMessage to "{escaped_body}"',
            f'    make new to recipient at newMessage with properties {{email address:{{address:"{escaped_recipient}"}}}}'
        ]
        
        if cc_email:
            escaped_cc = escape_applescript(cc_email)
            script_parts.append(f'    make new cc recipient at newMessage with properties {{email address:{{address:"{escaped_cc}"}}}}')
        
        script_parts.extend([
            '    send newMessage',
            'end tell'
        ])
        
        script = '\n'.join(script_parts)
        success, output = run_applescript(script)
        
        if success:
            return f"Email sent successfully to: {recipient_email}"
        else:
            return f"Error sending email: {output}"
    
    except Exception as e:
        return f"Error sending email: {str(e)}"
 
@mcp.tool()
def open_compose_window(recipient_email: str, subject: str, body: str, from_account: Optional[str] = None, cc_email: Optional[str] = None, bcc_email: Optional[str] = None) -> str:
    """
    Open Outlook compose window with pre-filled content
    
    This MCP tool opens Outlook's new email window and pre-fills recipient, subject, and body,
    but does not auto-send. User can edit, add attachments, or adjust formatting before sending.
    
    Args:
        recipient_email (str): Recipient email address.
        subject (str): Email subject.
        body (str): Email body content. Supports multi-line text.
        from_account (str, optional): Sender account (for multi-account). Defaults to None.
        cc_email (str, optional): CC email address. Defaults to None.
        bcc_email (str, optional): BCC email address. Defaults to None.
    
    Returns:
        str: Operation status:
            - Success: Confirms window is opened
            - Failure: Shows error reason
    
    Examples:
        - Basic usage: open_compose_window(recipient_email="user@example.com", subject="Notice", body="Content")
        - Full options: open_compose_window(recipient_email="user@example.com", subject="Report", body="Details", cc_email="cc@example.com", bcc_email="bcc@example.com")
    
    Note:
        - Email is not auto-sent, user can edit before manual sending
        - Suitable for scenarios requiring attachments or formatting adjustments
        - User can close window to cancel sending
        - Requires Microsoft Outlook to be installed and running on macOS
    """
    try:
        ok, err = ensure_outlook_running()
        if not ok:
            return f"Error: {err}"
        
        escaped_subject = escape_applescript(subject or "")
        escaped_body = escape_applescript(body or "")
        escaped_recipient = escape_applescript(recipient_email or "")
        
        script_parts = [
            'tell application "Microsoft Outlook"',
            '    activate',
            '    set newMessage to make new outgoing message',
            f'    set subject of newMessage to "{escaped_subject}"',
            f'    set content of newMessage to "{escaped_body}"',
            f'    make new to recipient at newMessage with properties {{email address:{{address:"{escaped_recipient}"}}}}'
        ]
        
        if cc_email:
            escaped_cc = escape_applescript(cc_email)
            script_parts.append(f'    make new cc recipient at newMessage with properties {{email address:{{address:"{escaped_cc}"}}}}')
        
        if bcc_email:
            escaped_bcc = escape_applescript(bcc_email)
            script_parts.append(f'    make new bcc recipient at newMessage with properties {{email address:{{address:"{escaped_bcc}"}}}}')
        
        script_parts.extend([
            '    open newMessage',
            'end tell'
        ])
        
        script = '\n'.join(script_parts)
        success, output = run_applescript(script)
        
        if success:
            return "Compose window opened with recipient, subject, and body pre-filled."
        else:
            return f"Error opening compose window: {output}"
    
    except Exception as e:
        return f"Error opening compose window: {str(e)}"
 
# Run the server
if __name__ == "__main__":
    print("Starting Outlook MCP Server (macOS version)...")
    print("Checking Outlook connection...")
    
    try:
        if check_outlook_running():
            print("Successfully connected to Outlook.")
        else:
            print("Warning: Outlook is not currently running. Server will start, but tools will require Outlook to be running.")
        
        print("Starting MCP server. Press Ctrl+C to stop.")
        mcp.run(transport="sse", host="127.0.0.1", port=8000)
    except Exception as e:
        print(f"Error starting server: {str(e)}")