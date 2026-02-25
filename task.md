# Task: Deep Dive on Reward Error causing Login Lockout

- [x] Audit `modules/mission/reward_handler.py` for `KeyError` vulnerabilities and unsafe DB writes. <!-- id: 0 -->
- [x] Audit `modules/ui_components.py` for error swallowing or unsafe re-runs. <!-- id: 1 -->
- [x] Inspect `db_manager.get_data` for retry logic. <!-- id: 2 -->
- [x] **Crucial Step**: Implement retry logic in `get_data` and ensure `ttl=0` bypasses cache. <!-- id: 3 -->
- [x] Verify fix (Code logic verified). <!-- id: 4 -->
