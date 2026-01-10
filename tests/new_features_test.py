import sys
import io
import os
import pandas as pd
from datetime import datetime

# Force UTF-8 encoding for stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.db_manager import db_manager

def test_calendar():
    print("\n[Test] Calendar CRUD...")
    # Add
    db_manager.add_calendar_event("2025-05-05", "Test Event", "가족 전체", "가족행사")
    df = db_manager.get_calendar()
    assert not df.empty
    found = df[df["title"] == "Test Event"]
    assert not found.empty
    print("  - Add Success")
    
    # Update
    event_id = found.iloc[0]["event_id"]
    db_manager.update_calendar_event(event_id, "2025-05-05", "Updated Event", "가족 전체", "가족행사")
    df = db_manager.get_calendar()
    assert df[df["event_id"] == str(event_id)].iloc[0]["title"] == "Updated Event"
    print("  - Update Success")
    
    # Delete
    db_manager.delete_calendar_event(event_id)
    df = db_manager.get_calendar()
    assert df[df["event_id"] == str(event_id)].empty
    print("  - Delete Success")

def test_reading():
    print("\n[Test] Reading Log Add...")
    db_manager.add_reading_log("2025-01-01", "Book", "Test Title", "Author", "Great", "son1")
    df = db_manager.get_reading_logs()
    assert not df.empty
    assert not df[df["book_title"] == "Test Title"].empty
    print("  - Add Success")

def test_praise():
    print("\n[Test] Praise Request & Approve...")
    # Add Request with unique content to avoid collision
    unique_content = f"Test Praise {pd.Timestamp.now()}"
    db_manager.add_praise_request(unique_content, "son1")
    df = db_manager.get_praise_logs()
    found = df[df["content"] == unique_content]
    assert not found.empty
    assert found.iloc[0]["status"] == "Pending"
    print("  - Add Request Success")
    
    # Approve
    praise_id = found.iloc[0]["praise_id"]
    db_manager.update_praise_status(praise_id, "Completed")
    df = db_manager.get_praise_logs()
    assert df[df["praise_id"] == str(praise_id)].iloc[0]["status"] == "Completed"
    print("  - Approve Success")

def test_settings():
    print("\n[Test] Settings Update...")
    # Mock update
    new_settings = pd.DataFrame([
        {"category": "Reward", "item_name": "TestItem", "value": 500, "unit": "원"}
    ])
    db_manager.update_data("Settings", new_settings)
    df = db_manager.get_settings()
    assert not df.empty
    assert df.iloc[0]["item_name"] == "TestItem"
    print("  - Update Success")

if __name__ == "__main__":
    print("🚀 Starting New Features Test...")
    try:
        test_calendar()
        test_reading()
        test_praise()
        test_settings()
        print("\n✅ All New Features Verified!")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
