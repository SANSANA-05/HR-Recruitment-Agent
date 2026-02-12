import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_candidate_name(user_message):
    prompt = f"""
Extract only the candidate name from this sentence.
If no name is present, reply with NONE.
Return ONLY the name.

Sentence:
"{user_message}"
"""

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    name = response.choices[0].message.content.strip()

    if name.upper() == "NONE":
        return None

    # extra safety cleaning
    name = re.sub(r"[^a-zA-Z]", "", name)
    return name
