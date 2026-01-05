import pytest
import os
import pandas as pd
import datetime
from unittest.mock import patch

# Import app
from app import create_app
# Import the MODULE, not just the class, so we can patch globals
import proxy_core as pc_module
from proxy_core import ProxyCore

@pytest.fixture
def mock_fs(tmp_path):
    """Creates temp folder structure."""
    (tmp_path / "Teacher_Timetables").mkdir()
    (tmp_path / "Absent_Lists").mkdir()
    (tmp_path / "Claims").mkdir()
    return tmp_path

@pytest.fixture
def core(mock_fs, monkeypatch):
    """
    Patches the GLOBAL variables in proxy_core.py to point to temp folders.
    This forces the static logic to use our test data.
    """
    # 1. Patch the MODULE-LEVEL constants in proxy_core.py
    # This redirects the actual logic inside the class
    monkeypatch.setattr(pc_module, "TIMETABLES_DIR", mock_fs / "Teacher_Timetables")
    monkeypatch.setattr(pc_module, "ABSENT_DIR", mock_fs / "Absent_Lists")
    monkeypatch.setattr(pc_module, "CLAIMS_CSV", mock_fs / "Claims" / "proxy_claims_data.csv")
    monkeypatch.setattr(pc_module, "CLAIMS_TXT", mock_fs / "Claims" / "proxy_claims_log.txt")

    # 2. Initialize Core (Now it uses the patched paths automatically)
    instance = ProxyCore()

    # 3. Inject missing Date Helpers (since they aren't in your static class)
    def get_today_date_str_mock():
        return datetime.date.today().strftime("%Y-%m-%d")

    def get_today_weekday_mock():
        return datetime.date.today().strftime("%A")

    instance.get_today_date_str = get_today_date_str_mock
    instance.get_today_weekday = get_today_weekday_mock
    
    # 4. Attach paths to instance so TESTS can find them (for setup_teacher_data)
    instance.timetables_path = mock_fs / "Teacher_Timetables"
    instance.absent_list_path = mock_fs / "Absent_Lists"
    instance.base_dir = mock_fs

    return instance

@pytest.fixture
def client(core):
    """
    Patches the shared 'proxy_core' instance in api.core_instance
    """
    # We patch the INSTANCE imported in api/core_instance.py
    with patch("api.core_instance.proxy_core", core):
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

@pytest.fixture
def setup_teacher_data(core):
    """Helper to create dummy data in the temp folder."""
    def _create(teacher_key, subject="AI", time_slot="09:00"):
        # Create Timetable Data
        tt_df = pd.DataFrame([{
            "TeacherKey": teacher_key,
            "TeacherDisplay": f"{teacher_key} Display",
            "Time": time_slot,
            "Department": "CS",
            "ClassOrLab": "Lab-A",
            "Subject": subject,
            "Day": core.get_today_weekday() 
        }])
        
        # Write to the TEMP path we attached to 'core'
        tt_path = core.timetables_path / f"{teacher_key}.csv"
        tt_df.to_csv(tt_path, index=False)
        return teacher_key
    return _create