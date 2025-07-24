from django.db import models

from configurations.models.base_model import BaseModel


class MemberAccount(BaseModel):
    member = models.ForeignKey('configurations.Member', on_delete=models.CASCADE, related_name="accounts")
    currency = models.ForeignKey('configurations.Currency', on_delete=models.CASCADE, related_name="member_accounts")

    # Account Balances
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Total Balance")
    available_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Available Balance")
    reserved_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Reserved Balance")

    # Account Limits
    credit_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Credit Limit")
    overdraft_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Overdraft Limit")

    # Account Status
    STATUS_CHOICES = [
        ("A", "Active"),
        ("S", "Suspended"),
        ("F", "Frozen"),
        ("C", "Closed"),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="A", verbose_name="Account Status")

    # Interest and Fees
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Interest Rate %")
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monthly Management Fee")

    # Parent Account (for sub-members/employees)

    def __str__(self):
        return f"{self.member.membership_number} - {self.currency.code}"

    class Meta:
        unique_together = [("member", "currency")]
        ordering = ["member__membership_number"]
        verbose_name = "Member Account"
        verbose_name_plural = "Member Accounts"

class MemberTransaction(BaseModel):
    account = models.ForeignKey(MemberAccount, on_delete=models.CASCADE, related_name="transactions")

    # Transaction Details
    transaction_number = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Transaction Number")

    TRANSACTION_TYPES = [
        ("D", "Deposit"),
        ("T", "Top-up"),
        ("C", "Claim Payment"),
        ("W", "Withdrawal"),
        ("F", "Fee"),
        ("R", "Reserve"),
        ("U", "Unreserve"),
        ("I", "Interest"),
        ("RF", "Refund"),
        ("TR", "Transfer In"),
        ("TO", "Transfer Out"),
        ("MF", "Microfinance"),
    ]
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPES, verbose_name="Transaction Type")

    # Amounts
    amount_debited = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Amount Debited")
    amount_credited = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Amount Credited")

    # Balances after transaction
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Balance After")
    available_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Available Balance After")

    # Transaction Details
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Description")
    reference = models.CharField(max_length=255, blank=True, null=True, verbose_name="Reference")

    # Links to other models
    claim = models.ForeignKey('services.Claim', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="member_transactions")
    top_up = models.ForeignKey('membership.TopUp', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="member_transactions")
    service_request = models.ForeignKey('services.ServiceRequest', on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name="member_transactions")

    # Transaction Status
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("C", "Completed"),
        ("F", "Failed"),
        ("R", "Reversed"),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P",
                              verbose_name="Transaction Status")

    # Processor information
    processed_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     verbose_name="Processed By")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Processed At")

    def save(self, *args, **kwargs):
        if not self.transaction_number:
            import datetime
            from sequences import Sequence
            date_str = datetime.datetime.now().strftime("%y%m%d")
            sequence_number = Sequence(f"member_transaction_{date_str}").get_next_value()
            self.transaction_number = f"MT{date_str}{sequence_number:06d}"

        # Set processed timestamp if completing
        if self.status == "C" and not self.processed_at:
            from django.utils import timezone
            self.processed_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_number} - {self.get_transaction_type_display()}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Member Transaction"
        verbose_name_plural = "Member Transactions"
