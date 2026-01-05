import os
import pandas as pd
import pytz
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

# --- CONFIGURATION ---
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR.parent / "data"
TT_DIR = DATA_DIR / "Teacher_Timetables"
ABSENT_DIR = DATA_DIR / "Absent_Lists"

# Define Timezone (Matches proxy_core.py)
IST = pytz.timezone('Asia/Kolkata')

def atomic_write_csv(df, target_path):
    """
    Writes a DataFrame to CSV atomically.
    Ensures the app never reads a partial file.
    """
    target_path = Path(target_path)
    temp_dir = target_path.parent
    temp_path = None
    
    try:
        # Create temp file in same folder to ensure atomic move
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, newline='', encoding='utf-8') as tmp:
            df.to_csv(tmp.name, index=False)
            temp_path = Path(tmp.name)
        
        # Atomic replacement
        shutil.move(str(temp_path), target_path)
        # On Windows, shutil.move might not overwrite implicitly in some versions, 
        # but os.replace does. Ideally os.replace is atomic POSIX standard.
        # For cross-platform safety in Python 3.11+:
        # os.replace(temp_path, target_path) is often preferred, but shutil handles cross-fs.
        # Given we are in same dir, os.replace is safe and atomic.
        
    except Exception as e:
        # Cleanup if write failed
        if temp_path and temp_path.exists():
            os.remove(temp_path)
        raise e

def setup_data():
    print(f"⚙️  Setting up test data in: {DATA_DIR}")

    # Ensure directories exist
    TT_DIR.mkdir(parents=True, exist_ok=True)
    ABSENT_DIR.mkdir(parents=True, exist_ok=True)

    # --- TIMEZONE AWARE "TODAY" ---
    current_day = datetime.now(IST).strftime("%A") 

    # --- TEACHER 1: Amit (Absent) ---
    amit_data = [
        {"Day": current_day, "Time": "10:00 AM", "Department": "CS", "ClassOrLab": "Lab 1", "Subject": "Python", "TeacherKey": "Amit"},
        {"Day": current_day, "Time": "11:00 AM", "Department": "CS", "ClassOrLab": "Room 101", "Subject": "DBMS", "TeacherKey": "Amit"},
        {"Day": current_day, "Time": "02:00 PM", "Department": "IT", "ClassOrLab": "Room 102", "Subject": "OS", "TeacherKey": "Amit"},
    ]
    atomic_write_csv(pd.DataFrame(amit_data), TT_DIR / "Amit_Timetable.csv")
    print(f"   ✅ Timetable: Amit ({current_day})")

    # --- TEACHER 2: You (Patel Sneha R) ---
    sneha_data = [
        {"Day": current_day, "Time": "09:00 AM", "Department": "CS", "ClassOrLab": "Room 200", "Subject": "Maths", "TeacherKey": "Patel Sneha R"},
    ]
    atomic_write_csv(pd.DataFrame(sneha_data), TT_DIR / "Patel_Sneha_R.csv")
    print(f"   ✅ Timetable: Patel Sneha R ({current_day})")

    # --- MARK ABSENT (Atomic Text Write) ---
    absent_file = ABSENT_DIR / "absent_today.txt"
    temp_absent = ABSENT_DIR / f"absent_{os.getpid()}.tmp"
    
    try:
        with open(temp_absent, "w", encoding='utf-8') as f:
            f.write("Amit\n")
        os.replace(temp_absent, absent_file)
        print(f"   ✅ Marked Absent: Amit")
    except Exception:
        if temp_absent.exists():
            os.remove(temp_absent)
        raise

    print(f"🎉 SUCCESS: Test data generated for {current_day} (IST)!\n")

if __name__ == "__main__":
    setup_data()