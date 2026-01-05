from flask import Blueprint, jsonify
from api.core_instance import proxy_core

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    # 1. Get keys of absent teachers
    absent_keys, err = proxy_core.get_todays_absent_keys()
    if err:
        return jsonify({"success": False, "message": err, "data": []}), 400

    # 2. Load dashboard data based on absent keys
    dashboard_df = proxy_core.load_dashboard_for_absent(absent_keys)
    
    # Handle empty or None dataframe safely
    if dashboard_df is None or dashboard_df.empty:
        return jsonify({"success": True, "message": "No unclaimed lectures for today", "data": []}), 200

    # 3. Format for JSON response
    # Reset index to make 'lecture_id' a column, then convert to dict
    records = dashboard_df.reset_index().rename(columns={"index": "lecture_id"}).to_dict(orient="records")
    
    return jsonify({"success": True, "message": "Dashboard loaded", "data": records}), 200