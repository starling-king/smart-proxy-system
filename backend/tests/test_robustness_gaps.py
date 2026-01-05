import pytest
import pandas as pd

def test_timetable_integration(client, core, setup_teacher_data):
    """
    Verifies that a CLAIMED lecture actually appears in the 'My Timetable' endpoint.
    Reference: "my status is active it also show in my timetables tab" [Source: 4]
    """
    # 1. Setup: Create Teacher A (Absent) and Proxy (You)
    setup_teacher_data("Teacher_A")
    (core.base_dir / "Absent_Lists" / "today.txt").write_text("Teacher_A")
    
    # Create a dummy timetable for YOU (Proxy) so we can see if they merge
    setup_teacher_data("My_Proxy_Account", subject="My Regular Class", time_slot="14:00")
    (core.base_dir / "Teacher_Timetables" / "My_Proxy_Account.csv").touch() # Verify existence

    # 2. Claim Teacher A's lecture
    # First, find the lecture ID from dashboard
    dash = client.get("/api/dashboard").get_json()["data"]
    target_id = dash[0]["lecture_id"]

    client.post("/api/claim", json={
        "proxy_key": "My_Proxy_Account",
        "lecture_id": target_id,
        "reason": "Helping out"
    })

    # 3. Check MY TIMETABLE
    resp = client.get("/api/my-timetable?proxy_key=My_Proxy_Account")
    data = resp.get_json()["data"]
    
    # Logic: Should have 2 entries (1 Regular + 1 Proxy)
    assert len(data) == 2
    
    # Verify the Proxy lecture is marked correctly
    proxy_lecture = next((x for x in data if x["Type"] == "Proxy"), None)
    assert proxy_lecture is not None
    assert proxy_lecture["TeacherKey"] == "Teacher_A"  # We are covering Teacher A

def test_cancel_removes_from_timetable(client, core, setup_teacher_data):
    """
    Verifies that CANCELLING a lecture removes it from 'My Timetable'.
    Reference: "cancled lecture remove from my timetable too" [Source: 5]
    """
    # 1. Setup & Claim (Reuse logic similar to above)
    setup_teacher_data("Teacher_B")
    (core.base_dir / "Absent_Lists" / "today.txt").write_text("Teacher_B")
    (core.base_dir / "Teacher_Timetables" / "Me.csv").touch()

    dash = client.get("/api/dashboard").get_json()["data"]
    client.post("/api/claim", json={
        "proxy_key": "Me",
        "lecture_id": dash[0]["lecture_id"],
        "reason": "Test"
    })

    # 2. Verify it is in Timetable initially
    resp_before = client.get("/api/my-timetable?proxy_key=Me")
    assert len(resp_before.get_json()["data"]) == 1

    # 3. Cancel It
    # Need the Claim ID from 'my-claims'
    claims_resp = client.get("/api/my-claims?proxy_key=Me")
    claim_id = claims_resp.get_json()["data"][0]["ClaimID"]

    client.post("/api/cancel", json={
        "proxy_key": "Me",
        "claim_id": claim_id
    })

    # 4. Verify it is GONE from Timetable
    resp_after = client.get("/api/my-timetable?proxy_key=Me")
    # Should be 0 because we had no regular lectures, only the proxy one
    assert len(resp_after.get_json()["data"]) == 0

def test_reclaim_cycle(client, core, setup_teacher_data):
    """
    Verifies you can Claim -> Cancel -> Re-Claim the SAME slot.
    Reference: "can cancle my claimed lecture ... and reclaim it again" [Source: 5]
    """
    setup_teacher_data("Teacher_C")
    (core.base_dir / "Absent_Lists" / "today.txt").write_text("Teacher_C")
    (core.base_dir / "Teacher_Timetables" / "Me.csv").touch()

    # --- Round 1: Claim ---
    dash1 = client.get("/api/dashboard").get_json()["data"]
    lecture_id = dash1[0]["lecture_id"]
    
    client.post("/api/claim", json={"proxy_key": "Me", "lecture_id": lecture_id, "reason": "1st try"})
    
    # --- Round 2: Cancel ---
    claim_id = client.get("/api/my-claims?proxy_key=Me").get_json()["data"][0]["ClaimID"]
    client.post("/api/cancel", json={"proxy_key": "Me", "claim_id": claim_id})

    # --- Round 3: Re-Claim ---
    # Lecture should be back on dashboard
    dash2 = client.get("/api/dashboard").get_json()["data"]
    assert len(dash2) == 1
    
    # Try to claim it again
    resp = client.post("/api/claim", json={
        "proxy_key": "Me", 
        "lecture_id": dash2[0]["lecture_id"], 
        "reason": "2nd try"
    })

    assert resp.status_code == 200
    assert resp.get_json()["success"] is True

    # Verify we now have a NEW active claim
    claims = client.get("/api/my-claims?proxy_key=Me").get_json()["data"]
    # We might have 2 records in history (1 cancelled, 1 active) depending on implementation
    # But we must have at least one ACTIVE
    active_claims = [c for c in claims if c["Status"] == "Active"]
    assert len(active_claims) == 1
    assert active_claims[0]["Reason"] == "2nd try"