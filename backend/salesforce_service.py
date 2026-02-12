def get_candidate(sf, search_type, value):
    base_query = """
    SELECT
        Id,
        Name,
        Candidate_ID__c,
        Candidate_Email__c,
        Application_Status__c,
        Interview_Date__c,
        Recruiter_Assigned__r.Name,
        Notes__c
    FROM Candidate__c
    """

    if search_type == "email":
        query = base_query + f"""
        WHERE Candidate_Email__c = '{value}'
        LIMIT 1
        """

    elif search_type == "id":
        query = base_query + f"""
        WHERE Candidate_ID__c = '{value}'
        LIMIT 1
        """

    else:  # name
        query = base_query + f"""
        WHERE Name LIKE '%{value}%'
        LIMIT 1
        """

    print("SOQL QUERY:", query)

    result = sf.query(query)
    return result.get("records", [])
