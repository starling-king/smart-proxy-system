import pytest

def test_dashboard_endpoint_empty(client):
    """Test dashboard when no teachers are absent."""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["data"]) == 0

def test_dashboard_endpoint_populated(client, core, setup_teacher_data):
    """Test dashboard when a teacher is absent."""
    setup_teacher_data("T1")
    (core.base_dir / "Absent_Lists" / "today.txt").write_text("T1")

    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["data"]) == 1
    assert data["data"][0]["TeacherKey"] == "T1"

def test_claim_lecture_validation(client):
    """Test validation (missing fields)."""
    resp = client.post("/api/claim", json={
        "proxy_key": "Me"
        # Missing lecture_id and reason
    })
    assert resp.status_code == 400
    assert "required" in resp.get_json()["message"]

def test_full_claim_flow(client, core, setup_teacher_data):
    """
    Full Scenario:
    1. Check Dashboard (Available)
    2. Claim Lecture
    3. Check Dashboard (Empty)
    4. Check My Claims
    """
    # Setup: Create a teacher "T_Target" who is absent
    setup_teacher_data("T_Target")
    (core.base_dir / "Absent_Lists" / "today.txt").write_text("T_Target")

    # 1. Get Dashboard
    dash_resp = client.get("/api/dashboard")
    lectures = dash_resp.get_json()["data"]
    lecture_id = lectures[0]["lecture_id"] # Get the dynamic ID

    # 2. Claim
    # FIX: Ensure 'Proxy_User' exists in the CORRECT folder (Teacher_Timetables) 
    # The proxy_core checks TIMETABLES_DIR for valid teachers.
    (core.base_dir / "Teacher_Timetables" / "Proxy_User.csv").touch()

    claim_resp = client.post("/api/claim", json={
        "proxy_key": "Proxy_User",
        "lecture_id": lecture_id,
        "reason": "Free time"
    })
    
    if claim_resp.status_code == 200:
        # 3. Check Dashboard Empty
        dash_resp_2 = client.get("/api/dashboard")
        assert len(dash_resp_2.get_json()["data"]) == 0

        # 4. Check My Claims
        my_claims_resp = client.get("/api/my-claims?proxy_key=Proxy_User")
        assert len(my_claims_resp.get_json()["data"]) == 1
    else:
        # Fail helpful message if setup was wrong
        pytest.fail(f"Claim failed: {claim_resp.get_json()}")