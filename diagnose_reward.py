from modules.db_manager import db_manager
import pandas as pd

def diagnose():
    print("--- Reward Sheet Diagnosis ---")
    try:
        # 1. Raw Data Load
        df = db_manager.get_data("Reward", ttl=0)
        print(f"Total Rows Found: {len(df)}")
        print(f"Columns Found: {df.columns.tolist()}")
        
        if not df.empty:
            print("\n--- Top 5 Rows (Raw) ---")
            # Convert to string without potential encoding issues
            print(df.head(5).to_string().encode('ascii', errors='replace').decode('ascii'))
            
            # 2. Check unique values for filtering columns
            for col in df.columns:
                unique_vals = df[col].unique()
                print(f"Unique values in [{col}]: {unique_vals}")

            # 3. Target Child search
            # We need to know who the target is. StressTestUser is a placeholder.
            # In Wallet.py, it's target_child_name.
            print("\n--- Potential User Matches ---")
            user_col = next((c for c in df.columns if str(c).lower() == 'user'), None)
            if user_col:
                all_users = df[user_col].unique()
                print(f"All Unique Users in sheet: {all_users}")
        else:
            print("Reward sheet is EMPTY.")
            
    except Exception as e:
        print(f"Diagnosis Failed: {e}")

if __name__ == "__main__":
    diagnose()
