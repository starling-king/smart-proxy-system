from flask import Blueprint, request, jsonify
from api.core_instance import proxy_core

timetable_bp = Blueprint("timetable", __name__)

@timetable_bp.route("/my-timetable", methods=["GET"])
def my_timetable():
    proxy_key = request.args.get("proxy_key", "").strip()
    if not proxy_key:
        return jsonify({"success": False, "message": "proxy_key is required", "data": []}), 400

    # 1. Verify Teacher Existence
    ok, msg = proxy_core.verify_teacher_exists(proxy_key)
    if not ok:
        return jsonify({"success": False, "message": msg, "data": []}), 404

    # 2. Load Timetable
    rows_or_err = proxy_core.load_raw_todays_for_teacher(proxy_key)
    
    # Check if result is an error string
    if isinstance(rows_or_err, str):
        return jsonify({"success": False, "message": rows_or_err, "data": []}), 400

    df = rows_or_err
    if df is None or df.empty:
        return jsonify({"success": True, "message": "No timetable rows for today", "data": []}), 200

    # 3. Format Data
    df = df.reset_index(drop=True).fillna("")
    records = df.to_dict(orient="records")
    
    # Assign temporary lecture_id based on index for frontend reference
    for i, r in enumerate(records):
        r["lecture_id"] = i

    return jsonify({"success": True, "message": "Timetable loaded", "data": records}), 200