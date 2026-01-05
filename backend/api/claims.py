from flask import Blueprint, request, jsonify
from api.core_instance import proxy_core

claims_bp = Blueprint("claims", __name__)

@claims_bp.route("/claim", methods=["POST"])
def claim_lecture():
    data = request.get_json(silent=True) or {}

    proxy_key = str(data.get("proxy_key", "")).strip()
    lecture_id = data.get("lecture_id") # Keep as raw initially
    reason = str(data.get("reason", "")).strip()

    # Strict validation
    if not proxy_key or lecture_id is None or not reason:
        return jsonify({"success": False, "message": "Missing required fields: proxy_key, lecture_id, or reason"}), 400

    # 1. Verify Teacher
    ok, err = proxy_core.verify_proxy_teacher_is_present(proxy_key)
    if not ok:
        return jsonify({"success": False, "message": err}), 401

    # 2. Get Absent Data to validate lecture availability
    absent_keys, err = proxy_core.get_todays_absent_keys()
    if err:
        return jsonify({"success": False, "message": err}), 400

    dashboard_df = proxy_core.load_dashboard_for_absent(absent_keys)
    if dashboard_df is None or dashboard_df.empty:
        return jsonify({"success": False, "message": "No lectures available to claim"}), 400

    # 3. Check if lecture_id exists in the current dashboard
    # Ensure ID types match (cast to int if the index is int)
    try:
        # Assuming index is int, try to cast input. If index is string, this might need adjustment.
        # However, usually checking `if x in index` handles types if they match naturally.
        if lecture_id not in dashboard_df.index:
             # Try casting to int just in case JSON sent "1" as a string
             if int(lecture_id) in dashboard_df.index:
                 lecture_id = int(lecture_id)
             else:
                 return jsonify({"success": False, "message": "Invalid lecture_id provided"}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Invalid lecture_id format"}), 400

    # 4. Record Claim
    row = dashboard_df.loc[lecture_id]
    new_claim = proxy_core.record_claim_for_row(row, proxy_key, reason)
    
    if new_claim is None or new_claim.empty:
        return jsonify({"success": False, "message": "Failed to record claim (Database error or race condition)"}), 500

    return jsonify({"success": True, "message": "Lecture claimed successfully"}), 200


@claims_bp.route("/my-claims", methods=["GET"])
def my_claims():
    proxy_key = request.args.get("proxy_key", "").strip()
    if not proxy_key:
        return jsonify({"success": False, "message": "proxy_key is required", "data": []}), 400

    df = proxy_core.get_my_claims_for_today(proxy_key)
    if df is None or df.empty:
        return jsonify({"success": True, "message": "No claims for today", "data": []}), 200

    # Handle NaN values for JSON safety
    df = df.fillna("")
    records = df.to_dict(orient="records")
    return jsonify({"success": True, "message": "My claims loaded", "data": records}), 200


@claims_bp.route("/cancel", methods=["POST"])
def cancel_claim():
    data = request.get_json(silent=True) or {}

    proxy_key = str(data.get("proxy_key", "")).strip()
    claim_id = data.get("claim_id")

    if not proxy_key or claim_id is None:
        return jsonify({"success": False, "message": "proxy_key and claim_id are required"}), 400

    try:
        claim_id = int(claim_id)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "claim_id must be a valid integer"}), 400

    ok, msg = proxy_core.cancel_claim_today(claim_id, proxy_key)
    if not ok:
        return jsonify({"success": False, "message": msg}), 400

    return jsonify({"success": True, "message": msg}), 200