import sys
import os
import toml
import bcrypt

# Force UTF-8 for Windows Console
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

print("=== User Migration: secrets.toml -> Google Sheets ===\n")

try:
    from modules.db_manager import db_manager
    import pandas as pd
    
    # 1. Read from secrets.toml
    secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml'))
    print(f"[1] Reading secrets.toml from: {secrets_path}")
    
    with open(secrets_path, "r", encoding="utf-8") as f:
        config = toml.load(f)
    
    if 'credentials' not in config or 'usernames' not in config['credentials']:
        print("[ERROR] No user credentials found in secrets.toml")
        sys.exit(1)
    
    users = config['credentials']['usernames']
    print(f"[OK] Found {len(users)} users in secrets.toml\n")
    
    # 2. Check existing Users sheet
    existing_df = db_manager.get_data("Users")
    
    if not existing_df.empty:
        print("[WARNING] Users sheet already has data:")
        print(existing_df[['username', 'name']].to_string(index=False))
        response = input("\nOverwrite existing data? (yes/no): ")
        if response.lower() != 'yes':
            print("[CANCELLED] Migration cancelled by user.")
            sys.exit(0)
    
    # 3. Prepare new data
    new_rows = []
    for username, user_data in users.items():
        new_rows.append({
            'username': username,
            'password': user_data.get('password', ''),
            'name': user_data.get('name', username),
            'email': user_data.get('email', ''),
            'role': 'admin' if username in ['dad', 'mom'] else 'user',
            'stamp_korea': user_data.get('stamp_korea', 0),
            'updated_at': ''
        })
    
    new_df = pd.DataFrame(new_rows)
    
    # 4. Update Google Sheets
    print("\n[2] Uploading to Google Sheets 'Users' table...")
    if db_manager.update_data("Users", new_df):
        print("[SUCCESS] Migration completed!")
        print(f"\nMigrated users: {', '.join(new_df['username'].tolist())}")
    else:
        print("[FAILED] Could not update Google Sheets")
        sys.exit(1)
        
except Exception as e:
    print(f"\n[CRITICAL ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
