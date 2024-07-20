ROLE_CHOICES = (
    ("chiefAdmin", "Chief Admin"), ("subAdmin1", "Sub Admin 1"), ("subAdmin2", "Sub Admin 2"),
    ("bankAdmin", "Bank Admin"), ("nonBankAdmin", "Non-Bank Admin"), ("bankUser1", "Bank User 1"),
    ("bankUser2", "Bank User 2"), ("nonBankUser1", "Non-Bank User 1"), ("nonBankUser2", "Non-Bank User 2")
)

INSTITUTION_TYPE_CHOICES = (
    ("bank", "Bank"), ("nonBank", "Non-Bank")
)

DASHBOARD_METRICS_CHOICES = (
    ("indicator", "indicator"), ("transactionReport", "Transaction Report"),
    ("transactionPerformance", "Transaction Performance"), ("institutionPerformance", "Institution Performance"),
    ("approvalRate", "Approval Rate")
)
