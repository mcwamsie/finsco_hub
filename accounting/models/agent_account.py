from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

from configurations.models import Agent, Currency
from configurations.models.base_model import BaseModel


class AgentAccount(BaseModel):
    """
    Account for tracking agent balances and commission transactions
    """
    agent = models.OneToOneField(
        Agent, 
        on_delete=models.CASCADE, 
        related_name="account",
        verbose_name="Agent"
    )
    currency = models.ForeignKey(
        Currency, 
        on_delete=models.CASCADE, 
        related_name="agent_accounts",
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
    
    # Commission Tracking
    total_commissions_earned = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Total Commissions Earned"
    )
    total_commissions_paid = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Total Commissions Paid"
    )
    pending_commissions = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Pending Commissions"
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
    
    # Withholding and Deductions
    total_withholding = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Total Withholding"
    )
    total_deductions = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Total Deductions"
    )
    
    # Payment Settings
    minimum_payout_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Minimum Payout Amount"
    )
    
    PAYOUT_FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("bi_weekly", "Bi-Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("on_demand", "On Demand"),
    ]
    payout_frequency = models.CharField(
        max_length=15, 
        choices=PAYOUT_FREQUENCY_CHOICES, 
        default="monthly",
        verbose_name="Payout Frequency"
    )
    
    # Account Status
    STATUS_CHOICES = [
        ("A", "Active"),
        ("I", "Inactive"),
        ("S", "Suspended"),
        ("C", "Closed"),
        ("H", "On Hold"),
    ]
    status = models.CharField(
        max_length=1, 
        choices=STATUS_CHOICES, 
        default="A",
        verbose_name="Account Status"
    )
    
    # Payment Method
    preferred_payment_method = models.ForeignKey(
        'configurations.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_accounts",
        verbose_name="Preferred Payment Method"
    )
    
    # Bank Details (for direct payments)
    bank_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Bank Name"
    )
    bank_account_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Bank Account Number"
    )
    bank_routing_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Bank Routing Number"
    )
    bank_account_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Bank Account Name"
    )
    
    # Tax Information
    tax_id_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Tax ID Number"
    )
    withholding_tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Withholding Tax Rate %"
    )
    
    # Last Payment Information
    last_payout_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Last Payout Date"
    )
    last_payout_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Last Payout Amount"
    )
    next_payout_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Next Payout Date"
    )
    
    def __str__(self):
        return f"{self.agent.name} Account ({self.currency.code})"
    
    @property
    def commission_balance(self):
        """Calculate available commission balance for payout"""
        return self.total_commissions_earned - self.total_commissions_paid - self.total_withholding
    
    @property
    def is_eligible_for_payout(self):
        """Check if agent is eligible for payout based on minimum amount"""
        return self.commission_balance >= self.minimum_payout_amount
    
    class Meta:
        ordering = ["agent__name"]
        verbose_name = "Agent Account"
        verbose_name_plural = "Agent Accounts"
        unique_together = [("agent", "currency")]


class AgentTransaction(BaseModel):
    """
    Transaction records for agent accounts
    """
    account = models.ForeignKey(
        AgentAccount, 
        on_delete=models.CASCADE, 
        related_name="transactions",
        verbose_name="Agent Account"
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
        ("commission_earned", "Commission Earned"),
        ("commission_payout", "Commission Payout"),
        ("bonus", "Bonus Payment"),
        ("deduction", "Deduction"),
        ("withholding", "Tax Withholding"),
        ("adjustment", "Manual Adjustment"),
        ("refund", "Refund"),
        ("chargeback", "Chargeback"),
        ("penalty", "Penalty"),
        ("advance", "Advance Payment"),
        ("advance_recovery", "Advance Recovery"),
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
    
    # Withholding and Deductions
    withholding_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Withholding Amount"
    )
    deduction_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Deduction Amount"
    )
    
    # Net Amount (after withholding and deductions)
    net_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name="Net Amount"
    )
    
    # Balances After Transaction
    balance_after = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        verbose_name="Balance After Transaction"
    )
    commission_balance_after = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        verbose_name="Commission Balance After"
    )
    
    # Transaction Details
    description = models.TextField(verbose_name="Description")
    reference_number = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Reference Number"
    )
    
    # Related Records
    agent_commission = models.ForeignKey(
        'configurations.AgentCommission',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_transactions",
        verbose_name="Related Commission"
    )
    member_transaction = models.ForeignKey(
        'accounting.MemberTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_transactions",
        verbose_name="Related Member Transaction"
    )
    
    # Period Information (for commission transactions)
    commission_period_from = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Commission Period From"
    )
    commission_period_to = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Commission Period To"
    )
    
    # Payment Information
    payment_method = models.ForeignKey(
        'configurations.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_transactions",
        verbose_name="Payment Method"
    )
    payment_reference = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Payment Reference"
    )
    payment_date = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Payment Date"
    )
    
    # Transaction Status
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("A", "Approved"),
        ("C", "Completed"),
        ("F", "Failed"),
        ("R", "Reversed"),
        ("H", "On Hold"),
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
        related_name="processed_agent_transactions",
        verbose_name="Processed By"
    )
    processed_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Processed At"
    )
    approved_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_agent_transactions",
        verbose_name="Approved By"
    )
    approved_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Approved At"
    )
    
    # Tax Information
    tax_year = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name="Tax Year"
    )
    tax_period = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        verbose_name="Tax Period"
    )
    
    def save(self, *args, **kwargs):
        if not self.transaction_number:
            import datetime
            from sequences import Sequence
            date_str = datetime.datetime.now().strftime("%y%m%d")
            sequence_number = Sequence(f"agent_transaction_{date_str}").get_next_value()
            self.transaction_number = f"AGT{date_str}{sequence_number:06d}"
        
        # Calculate net amount
        if self.transaction_type in ['commission_earned', 'bonus']:
            self.net_amount = self.credited_amount - self.withholding_amount - self.deduction_amount
        elif self.transaction_type in ['commission_payout', 'deduction', 'withholding']:
            self.net_amount = self.debited_amount
        else:
            self.net_amount = self.credited_amount - self.debited_amount
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.transaction_number} - {self.account.agent.name}"
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Agent Transaction"
        verbose_name_plural = "Agent Transactions"