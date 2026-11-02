import os
import requests
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)   

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

@app.route("/api/download-chembl", methods=["POST"])
def download_chembl():
    try:
        data = request.get_json()
        protein_query = data.get("protein_query", "Epidermal growth factor receptor")
        max_records = data.get("max_records", 100000)
        
        # 1. جلب Target ID
        if protein_query.upper().startswith("CHEMBL"):
            target_chembl_id = protein_query.upper()
            target_pref_name = protein_query
        else:
            target_url = f"{BASE_URL}/target"
            target_params = {"pref_name__icontains": protein_query, "format": "json", "limit": 100}
            resp = requests.get(target_url, params=target_params, timeout=30)
            resp.raise_for_status()
            targets = resp.json().get("targets", [])

            if not targets:
                return jsonify({"error": f"No ChEMBL target found for: {protein_query}"}), 404

            exact_matches = [t for t in targets if t.get("pref_name", "").lower() == protein_query.lower()]
            target = exact_matches[0] if exact_matches else targets[0]
            target_chembl_id = target["target_chembl_id"]
            target_pref_name = target.get("pref_name", protein_query)

        # 2. جلب الأنشطة IC50
        activity_url = f"{BASE_URL}/activity"
        all_activities = []
        offset = 0

        while True:
            params = {
                "target_chembl_id": target_chembl_id,
                "standard_type": "IC50",
                "format": "json",
                "limit": 1000,
                "offset": offset
            }
            
            res = requests.get(activity_url, params=params, timeout=60)
            res.raise_for_status()
            activities = res.json().get("activities", [])

            if not activities:
                break

            all_activities.extend(activities)
            offset += len(activities)

            if len(all_activities) >= max_records:
                break

        df_raw = pd.DataFrame(all_activities)
        if df_raw.empty:
            return jsonify({"error": "No IC50 records found for this target."}), 404

        return jsonify({
            "status": "success",
            "target_name": target_pref_name,
            "chembl_id": target_chembl_id,
            "total_records": len(df_raw),
            "message": "Data retrieved successfully!"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
