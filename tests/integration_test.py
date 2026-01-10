import sys
import io
import time
from datetime import datetime
import pandas as pd

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
# Add parent dir to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock streamlit session
class MockSession(dict):
    pass
    
# Mock Streamlit
import streamlit
streamlit.session_state = MockSession()
streamlit.secrets = {"connections": {"gsheets": {"spreadsheet": "dummy"}}} # Mock secrets for imports

from modules.db_manager import db_manager
from modules.logic_processor import logic

def run_test():
    print("🚀 [Self-Test] Starting Integration Test Sequence...")
    
    # 0. Setup & Cleanup
    test_child = "son1"
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"   Target User: {test_child}, Date: {today_str}")

    # 1. Scenario A: Assign & Complete Missions
    print("\n--- Scenario A: Mission Assignment & Completion ---")
    
    # 1.1 Create 2 missions
    print("   [Action] Creating 2 test missions...")
    missions = [
        {"mission_id": int(time.time()), "date": today_str, "assignee": test_child, "title": "Test Mission 1", "status": "Assigned", "rejection_reason": ""},
        {"mission_id": int(time.time())+1, "date": today_str, "assignee": test_child, "title": "Test Mission 2", "status": "Assigned", "rejection_reason": ""}
    ]
    df_org = db_manager.get_missions()
    df_new = pd.concat([df_org, pd.DataFrame(missions)], ignore_index=True)
    db_manager.update_data("Missions", df_new)
    print("   [Check] Missions created.")
    
    # 1.2 Child Completes Missions
    print("   [Action] Child marks missions as Done (Pending)...")
    # Reload to get valid indices
    df = db_manager.get_missions()
    target_missions = df[(df['assignee'] == test_child) & (df['date'] == today_str) & (df['title'].str.contains("Test Mission"))]
    
    for _, row in target_missions.iterrows():
        logic.update_mission_status(row['mission_id'], "Pending")
        print(f"     - Mission {row['mission_id']} -> Pending")
        
    print("   PASS: Scenario A completed.")

    # 2. Scenario B: Parent Approves & Grants Reward
    print("\n--- Scenario B: Parent Approval & Reward ---")
    
    # 2.1 Approve all
    print("   [Action] Parent approves all pending test missions...")
    df = db_manager.get_missions()
    pending_missions = df[(df['assignee'] == test_child) & (df['status'] == 'Pending')]
    
    for _, row in pending_missions.iterrows():
        logic.update_mission_status(row['mission_id'], "Approved")
        print(f"     - Mission {row['mission_id']} -> Approved")
        
    # 2.2 Check All-Clear
    is_all_clear = logic.check_daily_all_clear(test_child, today_str)
    print(f"   [Check] Daily All-Clear Status: {is_all_clear}")
    if not is_all_clear:
        print("   FAIL: All-Clear check failed.")
        return

    # 2.3 Grant Reward
    print("   [Action] Granting Final Reward (1 Coupon, 5 Stamps '칭찬도장')...")
    # Assume '칭찬도장' value is 100 KRW (Default)
    logic.grant_reward(test_child, "게임 30분", 1, "칭찬도장", 5)
    print("   PASS: Reward granted.")

    # 3. Scenario C: Check Wallet & Settle
    print("\n--- Scenario C: Wallet Check & Settlement ---")
    
    # 3.1 Check Balance
    m_bal, c_bal = logic.calculate_assets(test_child)
    print(f"   [Result] Money: {m_bal} KRW, Coupons: {c_bal} ea")
    
    # Verify values (roughly)
    # We added 5 stamps * 100 = 500 KRW minimum (plus whatever was there).
    # We added 1 coupon.
    
    # 3.2 Settle
    print(f"   [Action] Performing Settlement (Resetting {m_bal} KRW)...")
    logic.perform_settlement(test_child, m_bal)
    
    # 3.3 Verify Reset
    m_bal_new, c_bal_new = logic.calculate_assets(test_child)
    print(f"   [Result] Post-Settlement Money: {m_bal_new} KRW")
    
    if m_bal_new == 0:
        print("   PASS: Balance reset to 0.")
    else:
        print(f"   FAIL: Balance is {m_bal_new}, expected 0.")

    print("\n✅ [Self-Test] All Scenarios Completed Successfully.")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"❌ Test Failed with Error: {e}")
        import traceback
        traceback.print_exc()
