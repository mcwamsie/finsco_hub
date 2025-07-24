from django.db import models

# Create your models here.


# services/models/service_request.py


# Pre-populate AdjudicationMessageCode with standard codes
class AdjudicationMessageCodeData:
    """Standard adjudication message codes to be loaded as fixtures"""

    STANDARD_CODES = [
        # Beneficiary Messages (BENF)
        ("BENF001", "Beneficiary Inactive", "Beneficiary account is not active", "ERROR"),
        ("BENF002", "Benefits Not Started", "Benefits start date is in the future", "ERROR"),
        ("BENF003", "Beneficiary Suspended", "Beneficiary is currently suspended", "ERROR"),
        ("BENF004", "Beneficiary Terminated", "Beneficiary account has been terminated", "ERROR"),
        ("BENF100", "Eligibility Confirmed", "Beneficiary is eligible for benefits", "INFO"),

        # Limit Messages (LIMT)
        ("LIMT001", "Partial Approval - Annual Limit", "Amount reduced to remaining annual limit", "WARNING"),
        ("LIMT002", "Annual Limit Exceeded", "Beneficiary has exceeded annual limit", "ERROR"),
        ("LIMT003", "Partial Authorization", "Amount reduced to remaining limit", "WARNING"),
        ("LIMT004", "Insufficient Limit", "Insufficient annual limit for this authorization", "ERROR"),
        ("LIMT005", "Category Limit Applied", "Category-specific limit has been applied", "WARNING"),
        ("LIMT006", "Category Limit Exceeded", "Category annual limit exceeded", "ERROR"),

        # Account Messages (ACCT)
        ("ACCT001", "Insufficient Funds", "Amount reduced to available balance", "WARNING"),
        ("ACCT002", "No Funds Available", "Insufficient account balance", "ERROR"),
        ("ACCT003", "No Account Found", "Member account not found", "ERROR"),
        ("ACCT004", "Limited Funds", "Authorization may exceed available funds", "WARNING"),
        ("ACCT005", "Account Check Failed", "Could not verify account balance", "WARNING"),

        # Fraud Messages (FRAU)
        ("FRAU001", "Duplicate Claim Detected", "Similar claim found within timeframe", "ERROR"),
        ("FRAU002", "High Claim Frequency", "Unusually high number of recent claims", "WARNING"),
        ("FRAU003", "Unusually High Amount", "Claim amount significantly higher than average", "WARNING"),
        ("FRAU004", "Provider Pattern Alert", "Unusual pattern detected for this provider", "WARNING"),
        ("FRAU005", "Beneficiary Pattern Alert", "Unusual claiming pattern for beneficiary", "WARNING"),

        # Authorization Messages (AUTH)
        ("AUTH001", "Authorization Required", "This service requires prior authorization", "ERROR"),
        ("AUTH002", "Authorization Found", "Valid authorization exists for this service", "INFO"),
        ("AUTH003", "Authorization Expired", "Authorization has expired", "ERROR"),
        ("AUTH004", "Authorization Utilized", "Authorization has been fully utilized", "ERROR"),
        ("AUTH005", "Partial Authorization", "Partial authorization amount available", "WARNING"),

        # Provider Messages (PROV)
        ("PROV001", "Provider Inactive", "Service provider is not active", "ERROR"),
        ("PROV002", "Provider Suspended", "Service provider is suspended", "ERROR"),
        ("PROV003", "Provider Not Contracted", "Provider is not contracted for this service", "ERROR"),
        ("PROV004", "Document Missing", "Required provider document is missing", "WARNING"),
        ("PROV005", "Document Expired", "Provider document has expired", "WARNING"),

        # Service Messages (SERV)
        ("SERV001", "Service Not Covered", "Service is not covered under this plan", "ERROR"),
        ("SERV002", "Service Requires Referral", "Service requires a valid referral", "ERROR"),
        ("SERV003", "Emergency Service", "Service identified as emergency", "INFO"),
        ("SERV004", "Wellness Service", "Service identified as wellness/preventive", "INFO"),
        ("SERV005", "Chronic Condition", "Service related to chronic condition", "INFO"),

        # Package Messages (PACK)
        ("PACK001", "Package Limit Applied", "Package-specific limit has been applied", "WARNING"),
        ("PACK002", "Package Benefit Exhausted", "Package benefit has been exhausted", "ERROR"),
        ("PACK003", "Waiting Period Active", "Service is in waiting period", "ERROR"),
        ("PACK004", "Co-payment Applied", "Co-payment has been applied", "INFO"),

        # Age-related Messages (AGER)
        ("AGER001", "Age Restriction", "Service has age restrictions", "ERROR"),
        ("AGER002", "Pediatric Service", "Service approved for pediatric beneficiary", "INFO"),
        ("AGER003", "Geriatric Service", "Service approved for elderly beneficiary", "INFO"),

        # Time-related Messages (TIME)
        ("TIME001", "Service Too Old", "Service date exceeds allowable submission period", "ERROR"),
        ("TIME002", "Future Service Date", "Service date is in the future", "ERROR"),
        ("TIME003", "Same Day Service", "Multiple services on same day", "WARNING"),

        # Manual Review Messages (REVW)
        ("REVW001", "Manual Review Required", "Claim requires manual review", "WARNING"),
        ("REVW002", "Clinical Review Required", "Claim requires clinical review", "WARNING"),
        ("REVW003", "High Value Claim", "High value claim flagged for review", "WARNING"),
        ("REVW004", "Complex Case", "Complex case requires specialist review", "WARNING"),

        # Approval Messages (APPR)
        ("APPR001", "Auto Approved", "Claim automatically approved", "APPROVAL"),
        ("APPR002", "Manually Approved", "Claim approved after manual review", "APPROVAL"),
        ("APPR003", "Clinically Approved", "Claim approved after clinical review", "APPROVAL"),
        ("APPR004", "Conditionally Approved", "Claim approved with conditions", "APPROVAL"),

        # Decline Messages (DECL)
        ("DECL001", "Medical Necessity", "Service deemed not medically necessary", "DECLINE"),
        ("DECL002", "Policy Exclusion", "Service excluded under policy terms", "DECLINE"),
        ("DECL003", "Incomplete Information", "Insufficient information provided", "DECLINE"),
        ("DECL004", "Provider Issue", "Provider-related decline reason", "DECLINE"),
        ("DECL005", "Duplicate Service", "Duplicate service already paid", "DECLINE"),
    ]  # configurations/models/currency.py