from modules.db_manager import db_manager
import pandas as pd
from datetime import datetime
import modules.time_utils as time_utils

print("Initializing Cleanup v2...")

# 1. Load Missions
missions = db_manager.get_missions()
print(f"Total Missions in DB: {len(missions)}")

if missions.empty:
    print("Mission DB is empty.")
    exit()

# 2. Define Criteria
# We want to DELETE exact matches: assignee='son1' AND date='TODAY'
# But let's check what 'TODAY' looks like in the DB first.
today_dt = time_utils.get_now()
today_str = today_dt.strftime("%Y-%m-%d")

# Robust Filter
missions['date_str'] = missions['date'].astype(str)
missions['assignee_str'] = missions['assignee'].astype(str)

print("Dates in DB (str):", missions['date_str'].unique())
print("Assignees in DB (str):", missions['assignee_str'].unique())

target_user = "son1"
mask_son1 = missions['assignee_str'].str.contains(target_user)
son1_rows = missions[mask_son1]
print(f"Rows for {target_user}:")
print(son1_rows[['date_str', 'title', 'assignee_str']])

mask_date = missions['date_str'].str.contains(today_str)
mask_to_delete = mask_son1 & mask_date

count = mask_to_delete.sum()
print(f"Found {count} missions matching {target_user} on {today_str}")

if count > 0:
    # Get IDs to keep
    ids_to_delete = missions.loc[mask_to_delete, 'mission_id'].tolist()
    print(f"Deleting IDs: {ids_to_delete}")
    
    # Filter original dataframe (to preserve types if needed, or just use cleaned)
    # Better to filter by ID
    missions_cleaned = missions[~missions['mission_id'].isin(ids_to_delete)].copy()
    
    # Drop temp cols
    if 'date_str' in missions_cleaned.columns: del missions_cleaned['date_str']
    if 'assignee_str' in missions_cleaned.columns: del missions_cleaned['assignee_str']

    print(f"New count: {len(missions_cleaned)}")
    
    # Force update
    success = db_manager.update_data("Missions", missions_cleaned)
    if success:
        print("✅ UPDATE SUCCESSFUL.")
    else:
        print("❌ UPDATE FAILED.")
else:
    print("No ghost missions found to delete.")
