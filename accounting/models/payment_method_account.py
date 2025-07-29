from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

from configurations.models import PaymentMethod, Currency
from configurations.models.base_model import BaseModel


class PaymentMethodAccount(BaseModel):
    """
    Account for tracking payment method balances and transactions
    """
    payment_method = models.OneToOneField(
        PaymentMethod, 
        on_delete=models.CASCADE, 
        related_name="account",
        verbose_name="Payment Method"
    )
    currency = models.ForeignKey(
        Currency, 
        on_delete=models.CASCADE, 
        related_name="payment_method_accounts",
        verbose_name="Currency"
    )
    
    # Account Balances
    current_balance = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Current Balance"
    )
    available_balance = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Available Balance"
    )
    pending_balance = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Pending Balance"
    )
    
    # Cumulative Totals
    total_debited = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Total Debited"
    )
    total_credited = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Total Credited"
    )
    
    # Processing Fees
    total_processing_fees = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Total Processing Fees"
    )
    
    # Account Limits
    daily_transaction_limit = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Daily Transaction Limit"
    )
    monthly_transaction_limit = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Monthly Transaction Limit"
    )
    
    # Account Status
    STATUS_CHOICES = [
        ("A", "Active"),
        ("I", "Inactive"),
        ("S", "Suspended"),
        ("C", "Closed"),
    ]
    status = models.CharField(
        max_length=1, 
        choices=STATUS_CHOICES, 
        default="A",
        verbose_name="Account Status"
    )
    
    # Reconciliation
    last_reconciled_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Last Reconciled At"
    )
    reconciliation_variance = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Reconciliation Variance"
    )
    
    def __str__(self):
        return f"{self.payment_method.name} Account ({self.currency.code})"
    
    class Meta:
        ordering = ["payment_method__name"]
        verbose_name = "Payment Method Account"
        verbose_name_plural = "Payment Method Accounts"
        unique_together = [("payment_method", "currency")]


class PaymentMethodTransaction(BaseModel):
    """
    Transaction records for payment method accounts
    """
    account = models.ForeignKey(
        PaymentMethodAccount, 
        on_delete=models.CASCADE, 
        related_name="transactions",
        verbose_name="Payment Method Account"
    )
    
    # Transaction Identification
    transaction_number = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        verbose_name="Transaction Number"
    )
    
    # Transaction Type
    TRANSACTION_TYPES = [
        ("top_up", "Top-up Amount"),
        ("top_up_fee", "Top-up Processing Fee"),
        ("claim_payment", "Claim Payment"),
        ("claim_fee", "Claim Processing Fee"),
        ("transfer_in", "Transfer In"),
        ("transfer_out", "Transfer Out"),
        ("cash_deposit", "Cash Deposit"),
        ("cash_withdrawal", "Cash Withdrawal"),
        ("bank_deposit", "Bank Deposit"),
        ("bank_withdrawal", "Bank Withdrawal"),
        ("refund", "Refund"),
        ("adjustment", "Manual Adjustment"),
        ("reconciliation", "Reconciliation"),
        ("gateway_fee", "Gateway Fee"),
        ("settlement", "Settlement"),
        ("chargeback", "Chargeback"),
        ("provider_payment", "Provider Payment"),
        ("agent_commission", "Agent Commission Payment"),
        ("vendor_payment", "Vendor Payment"),
    ]
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPES,
        verbose_name="Transaction Type"
    )
    
    # Transaction Amounts
    debited_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Debited Amount"
    )
    credited_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Credited Amount"
    )
    
    # Processing Fee
    processing_fee = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Processing Fee"
    )
    
    # Balances After Transaction
    balance_after = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        verbose_name="Balance After Transaction"
    )
    available_balance_after = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        verbose_name="Available Balance After"
    )
    
    # Transaction Details
    description = models.TextField(verbose_name="Description")
    reference_number = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Reference Number"
    )
    external_reference = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="External Reference"
    )
    
    # Related Records
    member_transaction = models.ForeignKey(
        'accounting.MemberTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_method_transactions",
        verbose_name="Related Member Transaction"
    )
    provider_transaction = models.ForeignKey(
        'accounting.ProviderTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_method_transactions",
        verbose_name="Related Provider Transaction"
    )
    agent_transaction = models.ForeignKey(
        'accounting.AgentTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_method_transactions",
        verbose_name="Related Agent Transaction"
    )
    vendor = models.ForeignKey(
        'configurations.Vendor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_method_transactions",
        verbose_name="Related Vendor"
    )
    claim = models.ForeignKey(
        'services.Claim',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_method_transactions",
        verbose_name="Related Claim"
    )
    top_up = models.ForeignKey(
        'membership.TopUp',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_method_transactions",
        verbose_name="Related Top-up"
    )
    transfer_to_account = models.ForeignKey(
        PaymentMethodAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfer_from_transactions",
        verbose_name="Transfer To Account"
    )
    transfer_from_account = models.ForeignKey(
        PaymentMethodAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfer_to_transactions",
        verbose_name="Transfer From Account"
    )
    
    # Gateway Information
    gateway_transaction_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Gateway Transaction ID"
    )
    gateway_response_code = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Gateway Response Code"
    )
    gateway_response_message = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Gateway Response Message"
    )
    
    # Transaction Status
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("C", "Completed"),
        ("F", "Failed"),
        ("R", "Reversed"),
        ("S", "Settled"),
    ]
    status = models.CharField(
        max_length=1, 
        choices=STATUS_CHOICES, 
        default="P",
        verbose_name="Transaction Status"
    )
    
    # Processing Information
    processed_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_payment_method_transactions",
        verbose_name="Processed By"
    )
    processed_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Processed At"
    )
    
    # Settlement Information
    settlement_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Settlement Date"
    )
    settlement_reference = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Settlement Reference"
    )
    
    def save(self, *args, **kwargs):
        if not self.transaction_number:
            import datetime
            from sequences import Sequence
            date_str = datetime.datetime.now().strftime("%y%m%d")
            sequence_number = Sequence(f"pm_transaction_{date_str}").get_next_value()
            self.transaction_number = f"PMT{date_str}{sequence_number:06d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.transaction_number} - {self.account.payment_method.name}"
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Method Transaction"
        verbose_name_plural = "Payment Method Transactions"


class PaymentMethodTransfer(BaseModel):
    """
    Model for handling transfers between payment methods
    """
    # Transfer Identification
    transfer_number = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        verbose_name="Transfer Number"
    )
    
    # Source and Destination Accounts
    from_account = models.ForeignKey(
        PaymentMethodAccount,
        on_delete=models.CASCADE,
        related_name="outgoing_transfers",
        verbose_name="From Account"
    )
    to_account = models.ForeignKey(
        PaymentMethodAccount,
        on_delete=models.CASCADE,
        related_name="incoming_transfers",
        verbose_name="To Account"
    )
    
    # Transfer Details
    amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Transfer Amount"
    )
    transfer_fee = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Transfer Fee"
    )
    
    # Transfer Type
    TRANSFER_TYPES = [
        ("cash_deposit", "Cash Deposit to Bank"),
        ("cash_withdrawal", "Cash Withdrawal from Bank"),
        ("bank_transfer", "Bank to Bank Transfer"),
        ("wallet_transfer", "Wallet to Wallet Transfer"),
        ("general_transfer", "General Transfer"),
    ]
    transfer_type = models.CharField(
        max_length=20, 
        choices=TRANSFER_TYPES,
        verbose_name="Transfer Type"
    )
    
    # Transfer Status
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("C", "Completed"),
        ("F", "Failed"),
        ("R", "Reversed"),
    ]
    status = models.CharField(
        max_length=1, 
        choices=STATUS_CHOICES, 
        default="P",
        verbose_name="Transfer Status"
    )
    
    # Transfer Details
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    reference = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Reference"
    )
    
    # Processing Information
    processed_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_payment_method_transfers",
        verbose_name="Processed By"
    )
    processed_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Processed At"
    )
    
    # Related Transactions
    from_transaction = models.OneToOneField(
        PaymentMethodTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_transfer",
        verbose_name="From Transaction"
    )
    to_transaction = models.OneToOneField(
        PaymentMethodTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transfer",
        verbose_name="To Transaction"
    )
    
    def save(self, *args, **kwargs):
        if not self.transfer_number:
            import datetime
            from sequences import Sequence
            date_str = datetime.datetime.now().strftime("%y%m%d")
            sequence_number = Sequence(f"pm_transfer_{date_str}").get_next_value()
            self.transfer_number = f"PMX{date_str}{sequence_number:06d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.transfer_number} - {self.from_account.payment_method.name} to {self.to_account.payment_method.name}"
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment Method Transfer"
        verbose_name_plural = "Payment Method Transfers"