import re
from datetime import datetime
import pytz
from flask import Flask, request, jsonify, render_template
from simple_salesforce import Salesforce
# ---------------- SALESFORCE LOGIN ----------------
import os
sf = Salesforce(
    username=os.getenv("SF_USERNAME"),
    password=os.getenv("SF_PASSWORD"),
    security_token=os.getenv("SF_SECURITY_TOKEN"),
    domain=os.getenv("SF_DOMAIN", "test")
)
# ---------------- FLASK APP ----------------
app = Flask(__name__)
# ---------------- HELPERS ----------------
def format_date(value):
    if not value:
        return "Not Available"
    try:
        ist = pytz.timezone("Asia/Kolkata")
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
        return dt.astimezone(ist).strftime("%d %b %Y, %I:%M %p")
    except:
        return value
def safe(v):
    return v if v else "Not Available"
def identify_candidate(who):
    if "@" in who:
        return f"Candidate_Email__c = '{who}'"
    elif re.fullmatch(r"[A-Za-z]\d+", who):
        return f"Candidate_ID__c = '{who.upper()}'"
    else:
        return f"Name LIKE '%{who}%'"
# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_msg = request.json.get("message", "").strip()
        msg = user_msg.lower()
        # ================= UPDATE INTENT =================
        update_match = re.search(
            r"update\s+(?:the\s+)?(?P<field>email|status|recruiter|notes)\s+of\s+(?P<who>[a-zA-Z0-9@.\s]+?)\s+to\s+(?P<value>.+)",
            msg
        )
        if update_match:
            field = update_match.group("field")
            who = update_match.group("who").strip()
            new_value = update_match.group("value").strip()
            field_map = {
                "email": "Candidate_Email__c",
                "status": "Application_Status__c",
                "recruiter": "Recruiter_Assigned__c",
                "notes": "Notes__c"
            }
            sf_field = field_map[field]
            where = identify_candidate(who)
            query = f"""
            SELECT Id, Name, Candidate_ID__c
            FROM Candidate__c
            WHERE {where}
            """
            records = sf.query(query).get("records", [])
            if not records:
                return jsonify({
                    "reply": "I could not find any candidate matching the provided details."
                })
            if len(records) > 1:
                ids = [r.get("Candidate_ID__c") for r in records if r.get("Candidate_ID__c")]
                return jsonify({
                    "reply": f"Multiple candidates found. Please specify Candidate ID. Available IDs: {', '.join(ids)}."
                })
            candidate = records[0]
            # 🔥 UPDATE IN SALESFORCE
            sf.Candidate__c.update(candidate["Id"], {sf_field: new_value})
            return jsonify({
                "reply": f"The {field} of candidate {candidate['Name']} (ID: {candidate.get('Candidate_ID__c')}) has been updated to {new_value}."
            })
        # ================= READ MODE =================
        search_by = ""
        value = ""
        if "@" in user_msg:
            search_by = "email"
            value = re.search(r"[\w\.-]+@[\w\.-]+", user_msg).group()
        elif re.search(r"\b[A-Za-z]\d+\b", user_msg):
            search_by = "id"
            value = re.search(r"\b[A-Za-z]\d+\b", user_msg).group()
        else:
            match = re.search(r"(?:of|for)\s+([a-zA-Z]+)", msg)
            value = match.group(1) if match else msg
            value = re.sub(r"[^a-zA-Z]", "", value)
            search_by = "name"
        if search_by == "email":
            where = f"Candidate_Email__c = '{value}'"
        elif search_by == "id":
            where = f"Candidate_ID__c = '{value.upper()}'"
        else:
            where = f"Name LIKE '%{value}%'"
        query = f"""
        SELECT
            Id,
            Name,
            Candidate_ID__c,
            Candidate_Email__c,
            Application_Status__c,
            Interview_Date__c,
            Recruiter_Assigned__c,
            Notes__c
        FROM Candidate__c
        WHERE {where}
        """
        records = sf.query(query).get("records", [])
        if not records:
            return jsonify({"reply": "No candidate record was found."})
        if search_by == "name" and len(records) > 1:
            ids = [r.get("Candidate_ID__c") for r in records if r.get("Candidate_ID__c")]
            return jsonify({
                "reply": f"Multiple candidates found. Please specify Candidate ID. Available IDs: {', '.join(ids)}."
            })
        c = records[0]
        name = safe(c.get("Name"))
        if "email" in msg:
            reply = f"The email address of {name} is {safe(c.get('Candidate_Email__c'))}."
        elif "status" in msg:
            reply = f"The application status of {name} is {safe(c.get('Application_Status__c'))}."
        elif "interview" in msg:
            reply = f"The interview for {name} is scheduled on {format_date(c.get('Interview_Date__c'))}."
        elif "recruiter" in msg:
            reply = f"The recruiter assigned to {name} is {safe(c.get('Recruiter_Assigned__c'))}."
        else:
            reply = (
                f"{name}'s details: "
                f"Candidate ID is {safe(c.get('Candidate_ID__c'))}, "
                f"email is {safe(c.get('Candidate_Email__c'))}, "
                f"status is {safe(c.get('Application_Status__c'))}."
            )
        return jsonify({"reply": reply})
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"reply": "An unexpected error occurred."}), 500

# ---------------- RUN ----------------


if __name__ == "__main__":
    print("✅ HR Chatbot Backend Running")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


