import os
import shutil
import logging
import tempfile
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import pytz

# --- Configuration ---
# BASE_DIR = Path.cwd()
# CLAIMS_CSV = BASE_DIR / "proxy_claims_data.csv"
# CLAIMS_TXT = BASE_DIR / "proxy_claims_log.txt"
# TIMETABLES_DIR = BASE_DIR / "Teacher_Timetables"
# ABSENT_DIR = BASE_DIR / "Absent_Lists"
#
# --- 1. CONFIGURATION ---
# Get the folder where proxy_core.py lives (/app/backend)
BACKEND_DIR = Path(__file__).resolve().parent

# Go up one level to find the 'data' folder (/app/data)
DATA_DIR = BACKEND_DIR.parent / "data"

# Define all paths relative to DATA_DIR
CLAIMS_CSV = DATA_DIR / "proxy_claims_data.csv"
CLAIMS_TXT = DATA_DIR / "proxy_claims_log.txt"
TIMETABLES_DIR = DATA_DIR / "Teacher_Timetables"
ABSENT_DIR = DATA_DIR / "Absent_Lists"

    # ------------------------------------------------------------------
    # FIXED METHOD: _write_db
    # ------------------------------------------------------------------

# Setup Logging
logger = logging.getLogger("ProxyCore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

class ProxyCore:
    """
    The Brain of the Proxy System.
    Handles all logic for Claims, Cancellations, Dashboards, and Persistence.
    API-Compatible Version.
    Refactored for robustness, scalability, and maintainability.
    """
    
    # Canonical Schema for the Database
    COLUMNS = [
        "ClaimID", "Date", "Time", "Department", "ClassOrLab", 
        "Subject", "TeacherDisplay", "TeacherKey", "ProxyName", "Reason", 
        "Status", "ClaimTime", "CancelTime"
    ]

    def __init__(self):
        self._ensure_directories()
        self._initialize_database()

    def _ensure_directories(self):
        """Ensures all necessary directories exist."""
        try:
            TIMETABLES_DIR.mkdir(parents=True, exist_ok=True)
            ABSENT_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.critical(f"Failed to create directories: {e}")
            raise

    # ------------------------------------------------------------------
    # 1. Database Initialization (Smart & Safe)
    # ------------------------------------------------------------------
    def _initialize_database(self):
        """
        Checks DB health on startup. 
        Only backups if the file is genuinely corrupted or has wrong schema.
        """
        if not CLAIMS_CSV.exists():
            self._create_empty_db()
            return

        try:
            # Quick Check: Read header only to validate schema
            df = pd.read_csv(CLAIMS_CSV, nrows=0)
            missing_cols = [c for c in self.COLUMNS if c not in df.columns]
            
            if missing_cols:
                logger.warning(f"Schema mismatch (Missing: {missing_cols}). Repairing...")
                self._backup_and_recreate()
            
            # If readable and has columns, we are good. No backup spam.
            
        except Exception as e:
            logger.error(f"Database corrupted or unreadable: {e}. Recreating.")
            self._backup_and_recreate()

    def _create_empty_db(self):
        """Creates a fresh, empty database with the correct schema."""
        try:
            pd.DataFrame(columns=self.COLUMNS).to_csv(CLAIMS_CSV, index=False)
            logger.info(f"Created new empty database at {CLAIMS_CSV}")
        except Exception as e:
            logger.critical(f"Failed to create empty database: {e}")

    def _backup_and_recreate(self):
        """Backs up the current DB file and creates a fresh one."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = CLAIMS_CSV.with_suffix(f".{timestamp}.bak")
        try:
            if CLAIMS_CSV.exists():
                shutil.copy(CLAIMS_CSV, backup_path)
                logger.info(f"Backed up corrupt DB to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup corrupt DB: {e}")
        
        self._create_empty_db()

    # ------------------------------------------------------------------
    # 2. Helpers (Time & Keys)
    # ------------------------------------------------------------------
    def get_ist_now(self) -> datetime:
        """Returns current time in IST timezone."""
        return datetime.now(pytz.timezone("Asia/Kolkata"))

    def get_today_str(self) -> str:
        """Returns today's date as YYYY-MM-DD string."""
        return self.get_ist_now().strftime("%Y-%m-%d")

    def get_day_name(self) -> str:
        """Returns full weekday name (e.g., 'Monday')."""
        return self.get_ist_now().strftime("%A")

    def _normalize(self, text) -> str:
        """Standardizes text for robust comparison (lowercase, stripped, no spaces)."""
        if text is None:
            return ""
        return str(text).lower().strip().replace(" ", "")

    def _generate_fingerprint(self, row: dict) -> str:
        """
        Creates a Unique ID for a lecture slot. 
        Used to join Timetable slots with Database Claims.
        Key: Date_Time_Dept_Class_Subject_Teacher
        """
        parts = [
            row.get('Date', self.get_today_str()),
            row.get('Time', ''),
            row.get('Department', ''),
            row.get('ClassOrLab', ''),
            row.get('Subject', ''),
            row.get('TeacherKey', '')
        ]
        return "_".join([self._normalize(p) for p in parts])

    # ------------------------------------------------------------------
    # 3. API Specific Methods (Matching Blueprints)
    # ------------------------------------------------------------------

    # --- Auth & Verification ---
    def verify_proxy_teacher_is_present(self, proxy_key: str) -> Tuple[bool, str]:
        """Verifies if the teacher exists in the system (Robust check against timetables)."""
        if not proxy_key:
            return False, "Proxy key is empty"
        
        target = self._normalize(proxy_key)
        
        # Optimization: Check filename first (Fast Path)
        # Tries to find "Patel Sneha R.csv" or similar
        for f in TIMETABLES_DIR.glob("*.csv"):
            if self._normalize(f.stem) == target:
                return True, "OK"

        # Deep scan inside files (Slow Path, fallback)
        for f in TIMETABLES_DIR.glob("*.csv"):
            try:
                # Read only header first to check column existence
                df_head = pd.read_csv(f, nrows=0)
                if 'TeacherKey' not in df_head.columns:
                    continue
                    
                df = pd.read_csv(f, dtype=str).fillna("")
                if df['TeacherKey'].apply(self._normalize).eq(target).any():
                    return True, "OK"
            except Exception:
                continue
        
        return False, "Teacher not found in records"

    def verify_teacher_exists(self, proxy_key: str) -> Tuple[bool, str]:
        """Wrapper for verify_proxy_teacher_is_present."""
        return self.verify_proxy_teacher_is_present(proxy_key)

    # --- Dashboard Data ---
    def get_todays_absent_keys(self) -> Tuple[List[str], Optional[str]]:
        """Reads Absent_Lists folder for today's absent teachers."""
        absent_keys = set()
        try:
            if not ABSENT_DIR.exists():
                return [], None
                
            for f in ABSENT_DIR.glob("*"):
                if f.is_file():
                    try:
                        content = f.read_text(encoding='utf-8', errors='ignore').splitlines()
                        for line in content:
                            if line.strip():
                                absent_keys.add(line.strip())
                    except Exception as e:
                        logger.warning(f"Could not read absent file {f.name}: {e}")
                        
            return list(absent_keys), None
        except Exception as e:
            return [], str(e)

    def load_dashboard_for_absent(self, absent_keys: List[str]) -> pd.DataFrame:
        """
        Returns DataFrame of AVAILABLE slots.
        Logic: (All Absent Slots) - (Active Claims Today)
        """
        today_date = self.get_today_str()
        today_day = self.get_day_name()

        # 1. Fetch Timetables
        raw_slots = self._fetch_timetables(absent_keys, today_day)
        if not raw_slots:
            return pd.DataFrame()

        df_slots = pd.DataFrame(raw_slots)
        # Ensure 'Date' column exists for fingerprinting
        df_slots['Date'] = today_date

        # 2. Get Today's ACTIVE Claims
        claims_df = self._read_db()
        active_claims = pd.DataFrame()
        
        if not claims_df.empty:
            active_claims = claims_df[
                (claims_df['Date'] == today_date) & 
                (claims_df['Status'] == 'Active')
            ]

        # 3. Subtract Active Claims
        if not active_claims.empty:
            # Generate fingerprints for subtraction logic
            claimed_fps = set(active_claims.apply(lambda r: self._generate_fingerprint(r.to_dict()), axis=1))
            slot_fps = df_slots.apply(lambda r: self._generate_fingerprint(r.to_dict()), axis=1)
            
            # Filter out slots that match claimed fingerprints
            df_slots = df_slots[~slot_fps.isin(claimed_fps)]

        return df_slots

    # --- Claims ---
    def record_claim_for_row(self, row: Union[pd.Series, Dict], proxy_key: str, reason: str) -> pd.DataFrame:
        """
        1. Checks race condition.
        2. Appends to CSV (Atomic).
        3. Returns the new claim record as DataFrame.
        """
        try:
            if isinstance(row, pd.Series):
                row = row.to_dict()

            row['Date'] = self.get_today_str()
            fingerprint = self._generate_fingerprint(row)

            # Race Check: Re-read DB to be absolutely sure
            df = self._read_db()
            if not df.empty:
                today_claims = df[df['Date'] == row['Date']]
                for _, r in today_claims.iterrows():
                    if r['Status'] == 'Active':
                        if self._generate_fingerprint(r.to_dict()) == fingerprint:
                            logger.warning(f"Race condition detected for slot: {fingerprint}")
                            return pd.DataFrame() # Return empty on failure

            # Create Record
            # Use timestamp for unique ID
            claim_id = int(self.get_ist_now().timestamp() * 1000)
            
            new_record = {
                "ClaimID": claim_id,
                "Date": row['Date'],
                "Time": row.get('Time', ''),
                "Department": row.get('Department', ''),
                "ClassOrLab": row.get('ClassOrLab', ''),
                "Subject": row.get('Subject', ''),
                "TeacherDisplay": row.get('TeacherDisplay', row.get('TeacherKey', '')),
                "TeacherKey": row.get('TeacherKey', ''),
                "ProxyName": proxy_key,
                "Reason": reason,
                "Status": "Active",
                "ClaimTime": self.get_ist_now().strftime("%Y-%m-%d %H:%M:%S"),
                "CancelTime": ""
            }

            # Atomic Write
            self._append_to_db(new_record)
            self._log_human_readable(new_record, "CLAIMED")
            
            return pd.DataFrame([new_record])
            
        except Exception as e:
            logger.error(f"Error recording claim: {e}")
            return pd.DataFrame()

    def get_my_claims_for_today(self, proxy_key: str) -> pd.DataFrame:
        """Returns Active AND Cancelled claims for today."""
        df = self._read_db()
        if df.empty:
            return pd.DataFrame()
        
        today = self.get_today_str()
        mask = (df['Date'] == today) & (df['ProxyName'].apply(self._normalize) == self._normalize(proxy_key))
        return df[mask].copy()

    def cancel_claim_today(self, claim_id: int, proxy_key: str) -> Tuple[bool, str]:
        """
        Cancels a claim. Handles both direct ClaimID and frontend Index lookup.
        """
        try:
            df = self._read_db()
            if df.empty: return False, "Database empty."

            # 1. Standardize Input (Simple Integer conversion)
            try:
                target_input = int(claim_id)
            except ValueError:
                return False, "Invalid Claim ID format."

            target_real_id = str(target_input)

            # 2. SMART LOOKUP: Handle "Index vs ID" mismatch
            # If the ID is small (< 1,000,000), it is likely an array index from the frontend.
            # We must map this index to the REAL ClaimID from the database.
            if target_input < 1000000:
                logger.info(f"Received Index {target_input}, mapping to real ClaimID...")
                
                # Get the exact list the user sees (Today + Their Name)
                today = self.get_today_str()
                my_norm = self._normalize(proxy_key)
                
                # Filter exactly as the 'my_claims' API does
                mask_today = (df['Date'] == today) & (df['ProxyName'].apply(self._normalize) == my_norm)
                my_claims_view = df[mask_today]
                
                # If index is valid in this view
                if 0 <= target_input < len(my_claims_view):
                    # Get the real ID from the Nth row
                    target_real_id = str(my_claims_view.iloc[target_input]['ClaimID'])
                    logger.info(f"Mapped Index {target_input} -> ClaimID {target_real_id}")
                else:
                    return False, "Claim index out of range."

            # 3. Find the row with the Real ID
            # Clean matching: Ensure both are strings and stripped
            # Handle float strings (e.g. "123.0") if they exist
            db_ids = df['ClaimID'].astype(str).str.strip().replace(r'\.0$', '', regex=True)
            mask_id = db_ids == target_real_id.strip()

            if not mask_id.any():
                logger.warning(f"Claim ID {target_real_id} not found in DB.")
                return False, "Claim not found."

            idx = df.index[mask_id][0]
            
            # 4. Final Security Check (Ownership)
            if self._normalize(df.at[idx, 'ProxyName']) != self._normalize(proxy_key):
                return False, "You do not own this claim."
            
            # 5. Check Status
            if str(df.at[idx, 'Status']).strip().lower() == 'cancelled':
                return False, "Already cancelled."

            # 6. Update & Save
            df.at[idx, 'Status'] = 'Cancelled'
            df.at[idx, 'CancelTime'] = self.get_ist_now().strftime("%Y-%m-%d %H:%M:%S")

            self._write_db(df)
            self._log_human_readable(df.loc[idx].to_dict(), "CANCELLED")

            return True, "Claim cancelled successfully."

        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            return False, "Internal error."

    # --- Timetable ---
    def load_raw_todays_for_teacher(self, proxy_key: str) -> Union[pd.DataFrame, str]:
        """Returns the static timetable merged with active proxies, cleaner version."""
        try:
            today_day = self.get_day_name()
            
            # 1. Static Timetable (Regular Lectures)
            static_slots = self._fetch_timetables([proxy_key], today_day)
            
            # Add 'Type' and 'Details' to regular slots for consistency
            for s in static_slots:
                s['Type'] = 'Regular'
                s['Details'] = s.get('Department', '') # Use Dept as detail for regular
                s['Date'] = self.get_today_str()

            # 2. Get Active Proxy Claims (to merge into timetable view)
            my_claims_df = self.get_my_claims_for_today(proxy_key)
            
            if not my_claims_df.empty:
                # Filter ONLY Active claims
                active_proxies = my_claims_df[my_claims_df['Status'] == 'Active']
                
                for _, row in active_proxies.iterrows():
                    # --- CLEANUP STEP: Create a new, clean dict ---
                    # We do NOT use row.to_dict() because it has too much garbage.
                    cleaned_item = {
                        "Date": row.get('Date'),
                        "Time": row.get('Time'),
                        "Department": row.get('Department'),
                        "ClassOrLab": row.get('ClassOrLab'),
                        "Subject": row.get('Subject'),
                        "Type": "Proxy", 
                        "TeacherKey": row.get('TeacherKey'), # Original Teacher
                        # Create a readable details string
                        "Details": f"Covering for {row.get('TeacherKey', 'Unknown')}" 
                    }
                    static_slots.append(cleaned_item)

            if not static_slots:
                return pd.DataFrame()
            
            # Sort by Time (Optional, string sort)
            try:
                static_slots.sort(key=lambda x: x.get('Time', ''))
            except Exception:
                pass
                
            return pd.DataFrame(static_slots)
            
        except Exception as e:
            logger.error(f"Error loading timetable: {e}")
            return str(e)

    # ------------------------------------------------------------------
    # 4. Low-Level IO & Helpers
    # ------------------------------------------------------------------
    def _read_db(self) -> pd.DataFrame:
        """Reads the CSV safely."""
        try:
            if not CLAIMS_CSV.exists():
                return pd.DataFrame(columns=self.COLUMNS)
            # Read everything as string to prevent type issues
            return pd.read_csv(CLAIMS_CSV, dtype=str).fillna("")
        except Exception as e:
            logger.error(f"Read DB Error: {e}")
            return pd.DataFrame(columns=self.COLUMNS)

    def _write_db(self, df: pd.DataFrame):
        """Atomic Write: Write to temp -> Rename."""
        temp_file = None
        try:
            # FIX: We now use 'DATA_DIR' instead of the deleted 'BASE_DIR'
            with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=DATA_DIR, suffix='.tmp', newline='') as tmp:
                df.to_csv(tmp.name, index=False)
                temp_file = tmp.name
            
            # Atomic move
            shutil.move(temp_file, CLAIMS_CSV)
        except Exception as e:
            logger.error(f"Write DB Error: {e}")
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)


    def _append_to_db(self, record: Dict):
        """Appends a single record to the database."""
        current_df = self._read_db()
        new_df = pd.DataFrame([record])
        combined = pd.concat([current_df, new_df], ignore_index=True)
        self._write_db(combined)

    def _log_human_readable(self, record: Dict, action: str):
        """Appends a readable log entry to the TXT file."""
        try:
            entry = (
                f"[{action}] {self.get_ist_now().strftime('%H:%M:%S')}\n"
                f"Proxy: {record.get('ProxyName')} | Slot: {record.get('Time')} {record.get('ClassOrLab')}\n"
                f"Reason: {record.get('Reason')}\n"
                f"Status: {record.get('Status')}\n"
                f"{'-'*30}\n"
            )
            with open(CLAIMS_TXT, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.error(f"Log Error: {e}")

    def _fetch_timetables(self, teacher_keys: List[str], day: str) -> List[Dict]:
        """Fetches timetable slots for a list of teachers on a specific day."""
        slots = []
        targets = set(self._normalize(t) for t in teacher_keys)
        
        for f in TIMETABLES_DIR.glob("*.csv"):
            try:
                # Read CSV
                df = pd.read_csv(f, dtype=str).fillna("")
                
                if 'Day' in df.columns and 'TeacherKey' in df.columns:
                    # Filter Day
                    day_match = df[df['Day'].str.lower() == day.lower()]
                    
                    if not day_match.empty:
                        # Filter Teacher
                        mask = day_match['TeacherKey'].apply(self._normalize).isin(targets)
                        matched = day_match[mask]
                        slots.extend(matched.to_dict('records'))
            except Exception as e:
                logger.warning(f"Error reading timetable {f.name}: {e}")
                continue
                
        return slots