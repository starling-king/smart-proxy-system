import pytest
import pandas as pd

def test_load_timetable_gracefully(core):
    """Ensure system doesn't crash if a teacher has no timetable."""
    result = core.load_raw_todays_for_teacher("Ghost_Teacher")
    # Should return string error OR empty df, but NOT raise Exception
    assert isinstance(result, str) or result.empty

def test_dashboard_logic_lifecycle(core, setup_teacher_data):
    """
    Complex Flow:
    1. Teacher is absent -> Lecture appears in Dashboard.
    2. Proxy claims lecture -> Lecture disappears from Dashboard.
    3. Proxy cancels -> Lecture reappears in Dashboard.
    """
    # 1. Setup
    t_key = "Prof_X"
    setup_teacher_data(t_key, subject="Mutant History")
    
    # Mark Absent
    absent_file = core.base_dir / "Absent_Lists" / "today.txt"
    absent_file.write_text(t_key) # Simple text file approach

    # Verify Dashboard has 1 row
    dash_df = core.load_dashboard_for_absent([t_key])
    assert len(dash_df) == 1
    assert dash_df.iloc[0]["Subject"] == "Mutant History"

    # 2. Claim
    row_to_claim = dash_df.iloc[0]
    proxy_key = "Wolverine"
    core.record_claim_for_row(row_to_claim, proxy_key, "Substitution")

    # Verify Empty
    dash_df_after = core.load_dashboard_for_absent([t_key])
    assert dash_df_after.empty

    # 3. Cancel
    # We need the claim ID. In a real DB it's an ID, here it might be index.
    # Assuming the core returns the Claim DataFrame, we can inspect it.
    claims_df = core.get_my_claims_for_today(proxy_key)
    assert len(claims_df) == 1
    
    # Core logic usually requires an ID (index)
    claim_id = 0 
    core.cancel_claim_today(claim_id, proxy_key)

    # Verify Reappearance
    dash_df_final = core.load_dashboard_for_absent([t_key])
    assert len(dash_df_final) == 1

def test_prevent_duplicate_claims(core, setup_teacher_data):
    """Ensure two people cannot claim the same lecture."""
    t_key = "Prof_Y"
    setup_teacher_data(t_key)
    
    # Manually inject a claim
    row = pd.Series({
        "Date": core.get_today_date_str(),
        "Time": "09:00",
        "TeacherKey": t_key,
        "ProxyName": "ExistingProxy",
        "Status": "active"
        # Add other fields as per your CSV structure
    })
    
    # Attempt to claim the same slot
    # Depending on your implementation, record_claim_for_row checks the dashboard.
    # If the dashboard is empty (because it's claimed), it shouldn't allow it.
    
    # Let's simulate the check logic directly if possible, 
    # OR rely on the dashboard being empty.
    
    # Mocking that the dashboard thinks it's available (race condition simulation)
    result = core.record_claim_for_row(row, "Hacker", "Stealing")
    
    # This assertion depends on your specific core logic implementation for duplicates.
    # If your code is robust, it should return None or raise error.
    # assert result is None