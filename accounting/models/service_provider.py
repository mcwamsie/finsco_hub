from django.db import models

from configurations.models.base_model import BaseModel


class ProviderAccount(BaseModel):
    service_provider = models.ForeignKey('configurations.ServiceProvider', on_delete=models.CASCADE, related_name="accounts")
    currency = models.ForeignKey('configurations.Currency', on_delete=models.CASCADE, related_name="provider_accounts")

    # Account Balances
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Total Balance")
    available_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Available Balance")
    pending_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Pending Balance")
    withheld_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Withheld Balance")

    # Account Status
    STATUS_CHOICES = [
        ("A", "Active"),
        ("S", "Suspended"),
        ("F", "Frozen"),
        ("C", "Closed"),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="A",
                              verbose_name="Account Status")

    # Payment Settings
    payment_method = models.ForeignKey('configurations.PaymentMethod', on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="provider_accounts", verbose_name="Preferred Payment Method")
    minimum_payment_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Minimum Payment Amount")

    def __str__(self):
        return f"{self.service_provider.name} - {self.currency.code}"

    class Meta:
        unique_together = [("service_provider", "currency")]
        ordering = ["service_provider__name"]
        verbose_name = "Provider Account"
        verbose_name_plural = "Provider Accounts"

class ProviderTransaction(BaseModel):
    account = models.ForeignKey(ProviderAccount, on_delete=models.CASCADE, related_name="transactions")

    # Transaction Details
    transaction_number = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Transaction Number")

    TRANSACTION_TYPES = [
        ("C", "Claim Payment"),
        ("W", "Withdrawal"),
        ("F", "Fee"),
        ("P", "Penalty"),
        ("B", "Bonus"),
        ("A", "Adjustment"),
        ("WH", "Withholding"),
        ("WR", "Withholding Release"),
    ]
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPES,
                                        verbose_name="Transaction Type")

    # Amounts
    amount_debited = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Amount Debited")
    amount_credited = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Amount Credited")
    withheld_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Withheld Amount")

    # Balances after transaction
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Balance After")
    available_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0,  verbose_name="Available Balance After")
    withheld_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Withheld Balance After")

    # Transaction Details
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Description")
    reference = models.CharField(max_length=255, blank=True, null=True, verbose_name="Reference")

    # Withholding Details
    withholding_reason = models.TextField(blank=True, null=True, verbose_name="Withholding Reason")
    withholding_document_type = models.ForeignKey('configurations.ServiceProviderDocumentType', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Related Document Type")

    # Links to other models
    claim = models.ForeignKey('services.Claim', on_delete=models.SET_NULL, null=True, blank=True, related_name="provider_transactions")
    payment_statement = models.ForeignKey('services.ProviderPaymentStatement', on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name="transactions")

    # Transaction Status
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("C", "Completed"),
        ("F", "Failed"),
        ("R", "Reversed"),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P", verbose_name="Transaction Status")

    # Processor information
    processed_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Processed By")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Processed At")

    def save(self, *args, **kwargs):
        if not self.transaction_number:
            import datetime
            from sequences import Sequence
            date_str = datetime.datetime.now().strftime("%y%m%d")
            sequence_number = Sequence(f"provider_transaction_{date_str}").get_next_value()
            self.transaction_number = f"PT{date_str}{sequence_number:06d}"

        # Set processed timestamp if completing
        if self.status == "C" and not self.processed_at:
            from django.utils import timezone
            self.processed_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_number} - {self.get_transaction_type_display()}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Provider Transaction"
        verbose_name_plural = "Provider Transactions"