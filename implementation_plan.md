# Implementation Plan - Authentication Debugging

# Goal Description
The user is experiencing a "Incorrect ID or Password" error during login. Diagnostic scripts fail to run due to environment mismatch. This plan proposes injecting temporary logging code into the application to capture the authentication state and data during runtime.

## Proposed Changes

### Modules
#### [MODIFY] [db_manager.py](file:///d:/최민수/AI/바이브코딩/FamilyMIssionManger/modules/db_manager.py)
- Inject logic into `get_user_dict` to write loaded user data details (username, password hash length) to `debug_auth_log.txt`.
- Log when `Users` dataframe is empty.

## Verification Plan
### Manual Verification
- Ask the user to attempt login again.
- Inspect `debug_auth_log.txt` to see:
    - If user data is loaded from Google Sheets.
    - If password hashes exist and have correct length.
