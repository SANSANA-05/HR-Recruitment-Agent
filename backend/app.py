import os
import re
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pytz
from flask import Flask, request, jsonify, render_template
from simple_salesforce import Salesforce

# ---------------- SALESFORCE LOGIN ----------------
sf = Salesforce(
    username="winfomidev@winfomi.com.dev9",
    password="Sansana@05",
    security_token="T5dEyDG6OkMEuGCWwLInszTx",
    domain="test"
)

# ---------------- FLASK APP ----------------
app = Flask(__name__)

# ---------------- EMAIL CONFIG ----------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "sansanamurugan2005@gmail.com"     # 🔥 CHANGE
EMAIL_PASSWORD = "womntaniidphulwg"      # 🔥 CHANGE

# ---------------- HELPER FUNCTIONS ----------------
def safe(v):
    return v if v else "Not Available"


# 🔥 FIXED FORMAT DATE FUNCTION
def format_date(value):
    if not value:
        return "Not Available"
    try:
        # Handles: 2026-02-20T05:00:00.000+0000
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")

        # Convert UTC → IST
        ist = pytz.timezone("Asia/Kolkata")
        dt_ist = dt.astimezone(ist)

        return dt_ist.strftime("%d %b %Y, %I:%M %p")

    except Exception as e:
        print("Date Format Error:", e)
        return value


def identify_candidate(who):
    if "@" in who:
        return f"Candidate_Email__c = '{who}'"
    elif re.fullmatch(r"[A-Za-z]\d+", who):
        return f"Candidate_ID__c = '{who.upper()}'"
    else:
        return f"Name LIKE '%{who}%'"

def format_multiple_candidates(records):
    return "\n".join([
        f"{safe(r.get('Name'))} (ID: {safe(r.get('Candidate_ID__c'))})"
        for r in records
    ])

# 🔥 STRICT DATE FORMAT FOR UPDATE
def parse_datetime(date_str):
    try:
        date_str = date_str.upper()  # 🔥 important fix
        dt = datetime.strptime(date_str, "%d-%m-%Y %I:%M %p")

        ist = pytz.timezone("Asia/Kolkata")
        dt_ist = ist.localize(dt)

        dt_utc = dt_ist.astimezone(pytz.utc)

        salesforce_format = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        return dt_ist, salesforce_format

    except ValueError as e:
        print("Date Parse Error:", e)
        return None, None

    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y %I:%M %p")

        ist = pytz.timezone("Asia/Kolkata")
        dt_ist = ist.localize(dt)

        dt_utc = dt_ist.astimezone(pytz.utc)

        salesforce_format = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        return dt_ist, salesforce_format

    except ValueError:
        return None, None


# ---------------- EMAIL FUNCTION ----------------
def send_email(to_email, name, interview_date):
    subject = "Interview Scheduled"

    body = f"""
Dear {name},

Your interview has been scheduled on {interview_date}.

Please be available at the scheduled time.

Best Regards,
HR Team
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
    server.quit()


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_msg = request.json.get("message", "").strip()

        # ==================================================
        # ================= UPDATE MODE ====================
        # ==================================================

        update_match = re.search(
    r"update\s+(?:the\s+)?(?P<field>email|status|recruiter|notes|interview date)\s+of\s+(?P<who>[a-zA-Z0-9@.\s]+?)\s+to\s+(?P<value>.+)",
    user_msg,
    re.IGNORECASE
)

        if update_match:
            field = update_match.group("field")
            who = update_match.group("who").strip()
            new_value = update_match.group("value").strip()

            field_map = {
                "email": "Candidate_Email__c",
                "status": "Application_Status__c",
                "recruiter": "Recruiter_Assigned__c",
                "notes": "Notes__c",
                "interview date": "Interview_Date__c"
            }

            where = identify_candidate(who)

            query = f"""
            SELECT Id, Name, Candidate_ID__c, Candidate_Email__c
            FROM Candidate__c
            WHERE {where}
            """

            records = sf.query(query).get("records", [])

            if not records:
                return jsonify({"reply": "No candidate found."})

            if len(records) > 1:
                return jsonify({
                    "reply": f"Multiple candidates found:\n{format_multiple_candidates(records)}\n\nPlease specify Candidate ID."
                })

            candidate = records[0]

            # -------- INTERVIEW DATE UPDATE --------
            if field == "interview date":

                dt_ist, salesforce_dt = parse_datetime(new_value)

                if not dt_ist:
                    return jsonify({
                        "reply": "Invalid format. Use: DD-MM-YYYY HH:MM AM/PM\nExample: 20-02-2026 10:30 AM"
                    })

                sf.Candidate__c.update(
                    candidate["Id"],
                    {"Interview_Date__c": salesforce_dt}
                )

                formatted = dt_ist.strftime("%d %b %Y, %I:%M %p")

                try:
                    send_email(
        candidate["Candidate_Email__c"],
        candidate["Name"],
        formatted
    )
                except Exception as e:
                    print("Email error:", e)

                return jsonify({
                    "reply": f"Interview date updated successfully for {candidate['Name']} and email sent."
                })

            # -------- OTHER FIELD UPDATE --------
            sf.Candidate__c.update(
                candidate["Id"],
                {field_map[field]: new_value}
            )

            return jsonify({
                "reply": f"{field.capitalize()} updated successfully for {candidate['Name']}."
            })

        # ==================================================
        # ================= READ MODE ======================
        # ==================================================

        search_by = None
        value = None

        # Email
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", user_msg)
        if email_match:
            search_by = "email"
            value = email_match.group()

        # Candidate ID
        elif re.search(r"\b[A-Za-z]\d+\b", user_msg):
            search_by = "id"
            value = re.search(r"\b[A-Za-z]\d+\b", user_msg).group()

        # Name extraction
        else:
            name_match = re.search(r"(?:of|for)\s+([a-zA-Z]+)", msg)
            if name_match:
                search_by = "name"
                value = name_match.group(1)
            else:
                search_by = "name"
                value = user_msg.strip()

        if search_by == "email":
            where = f"Candidate_Email__c = '{value}'"
        elif search_by == "id":
            where = f"Candidate_ID__c = '{value.upper()}'"
        else:
            where = f"Name LIKE '%{value}%'"

        query = f"""
        SELECT Name, Candidate_ID__c, Candidate_Email__c,
               Application_Status__c, Interview_Date__c,
               Recruiter_Assigned__c, Notes__c
        FROM Candidate__c
        WHERE {where}
        """

        records = sf.query(query).get("records", [])

        if not records:
            return jsonify({"reply": "No candidate record found."})

        if search_by == "name" and len(records) > 1:
            return jsonify({
                "reply": f"Multiple candidates found:\n{format_multiple_candidates(records)}\n\nPlease specify Candidate ID."
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
        elif "notes" in msg:
            reply = f"The notes for {name} are: {safe(c.get('Notes__c'))}."
        else:
            reply = (
                f"{name}'s details:\n"
                f"Candidate ID: {safe(c.get('Candidate_ID__c'))}\n"
                f"Email: {safe(c.get('Candidate_Email__c'))}\n"
                f"Status: {safe(c.get('Application_Status__c'))}\n"
                f"Interview Date: {format_date(c.get('Interview_Date__c'))}\n"
                f"Recruiter: {safe(c.get('Recruiter_Assigned__c'))}\n"
                f"Notes: {safe(c.get('Notes__c'))}"
            )

        return jsonify({"reply": reply})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"reply": "An unexpected error occurred."}), 500


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
