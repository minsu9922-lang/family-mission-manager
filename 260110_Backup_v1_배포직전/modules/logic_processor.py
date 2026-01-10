import pandas as pd
from datetime import datetime
from modules.db_manager import db_manager

class LogicProcessor:
    def __init__(self):
        self.db = db_manager

    # --- Mission Logic ---
    def get_todays_missions(self, user_name):
        df = self.db.get_missions()
        today_str = datetime.now().strftime("%Y-%m-%d")
        return df[(df['assignee'] == user_name) & (df['date'] == today_str)]

    def update_mission_status(self, mission_id, new_status, reason=""):
        df = self.db.get_missions()
        idx = df[df['mission_id'] == mission_id].index
        if not idx.empty:
            df.loc[idx, 'status'] = new_status
            if reason:
                df.loc[idx, 'rejection_reason'] = reason
            return self.db.update_data("Missions", df)
        return False

    def check_daily_all_clear(self, child_id, date_str):
        df = self.db.get_missions()
        # Filter for child and date
        child_missions = df[(df['assignee'] == child_id) & (df['date'] == date_str)]
        
        if child_missions.empty:
            return False # No missions to clear
            
        # Check if all are 'Approved'
        all_approved = child_missions['status'].eq('Approved').all()
        return all_approved

    def grant_reward(self, user_name, coupon_item, coupon_qty, stamp_item, stamp_qty):
        success = True
        # Log Coupon
        if coupon_qty > 0:
            # We don't have separate return values for each log, assumiong DB always works if connected
            self.db.log_activity(user_name, "보상", f"쿠폰: {coupon_item}", coupon_qty)
        
        # Log Stamp
        if stamp_qty > 0:
            self.db.log_activity(user_name, "보상", f"도장: {stamp_item}", stamp_qty)
            
        return success

    # --- Wallet Logic ---
    def calculate_assets(self, user_name):
        logs = self.db.get_logs()
        settings = self.db.get_settings()
        
        user_logs = logs[logs['User'] == user_name]
        
        total_money = 0
        total_coupons = 0
        
        # Parse Settings
        stamp_settings = settings[settings['category'] == 'stamp']
        stamp_prices = {}
        for _, row in stamp_settings.iterrows():
            try:
                stamp_prices[row['item_name']] = int(pd.to_numeric(row['value'], errors='coerce'))
            except:
                continue
                
        if user_logs.empty:
            return 0, 0

        for _, row in user_logs.iterrows():
            log_type = row.get('Type', '')
            content = row.get('Content', '')
            try:
                qty = int(pd.to_numeric(row.get('Reward', 0), errors='coerce'))
            except:
                qty = 0
                
            if log_type == "보상":
                if "도장:" in content:
                    # Content format: "도장: {stamp_name}"
                    try:
                        stamp_name = content.split(":", 1)[1].strip()
                        unit_price = stamp_prices.get(stamp_name, 0)
                        total_money += (qty * unit_price)
                    except:
                        pass # Malformed content
                elif "쿠폰:" in content:
                    total_coupons += qty
                    
            elif log_type == "쿠폰사용":
                 total_coupons += qty # qty is logged as negative for usage
                 
            elif log_type == "정산":
                # Settlement logs a negative MONEY value directly in Reward?
                # or Qty?
                # In perform_settlement below, we log "금액차감" with negative current balance.
                # So here we just sum it up.
                total_money += qty
                
        return int(total_money), int(total_coupons)

    def perform_settlement(self, user_name, current_balance):
        if current_balance <= 0:
            return False
            
        # Log a negative entry to zero out the balance
        self.db.log_activity(user_name, "정산", "금액차감", -current_balance)
        return True

    def use_coupon(self, user_name):
        # Generic usage
        self.db.log_activity(user_name, "쿠폰사용", "쿠폰 사용", -1)
        return True

# Singleton
logic = LogicProcessor()
