import os
from simple_salesforce import Salesforce
from dotenv import load_dotenv

load_dotenv()

def get_salesforce_connection():
    return Salesforce(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN"),
        domain=os.getenv("SF_DOMAIN")
    )
