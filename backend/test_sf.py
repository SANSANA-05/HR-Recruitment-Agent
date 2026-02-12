from simple_salesforce import Salesforce

sf = Salesforce(
    username="winfomidev@winfomi.com.dev9",
    password="Welovewinfomi$7",
    security_token="gRJ29f2mZUVTcYfzt16dqb0pT",
    domain="test"  # remove if production org
)

result = sf.query("SELECT Id, Name FROM Candidate__c LIMIT 1")
print(result)
