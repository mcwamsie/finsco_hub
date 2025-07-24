from django.db import models

from configurations.models import Member
from configurations.models.base_model import BaseModel


class Agent(BaseModel):
    account_no = models.CharField(max_length=255, unique=True, editable=False, db_index=True, verbose_name="Agent Number")
    name = models.CharField(max_length=255, unique=True, verbose_name="Agent Name", db_index=True)
    alias = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name="Alias")
    identification_no = models.CharField(max_length=255, verbose_name="ID Number", blank=True, null=True)

    # Contact information
    address_line_1 = models.CharField(max_length=255, verbose_name="Address Line 1")
    address_line_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Address Line 2")
    address_line_3 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Address Line 3")

    mobile = models.CharField(max_length=20, verbose_name="Mobile Number")
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telephone")
    email = models.EmailField(max_length=255, verbose_name="Email Address")

    # Agent specific fields
    AGENT_TYPES = [
        ("I", "Individual"),
        ("C", "Corporate"),
        ("B", "Internal"),
    ]
    type = models.CharField(max_length=1, choices=AGENT_TYPES, default="I", verbose_name="Agent Type")

    # Commission settings
    base_commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Base Commission Rate %")

    # Status and dates
    status = models.CharField(max_length=1, choices=[("A", "Active"), ("I", "Inactive"), ("S", "Suspended")], default="A", verbose_name="Status")
    date_joined = models.DateField(auto_now_add=True, verbose_name="Date Joined")

    currency = models.ForeignKey('configurations.Currency', on_delete=models.CASCADE, verbose_name="Main Currency")

    def __str__(self):
        return self.name.upper()

    def save(self, *args, **kwargs):
        if not self.account_no:
            import datetime
            import random
            import string
            from sequences import Sequence
            month = datetime.datetime.now().strftime("%y%m")
            sequence_number = Sequence(f'agent_number-{month}').get_next_value()
            random_number = ''.join(random.choice(string.digits) for _ in range(2))
            self.account_no = "AG" + month + f"{sequence_number:04d}" + random_number
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["account_no"]
        verbose_name = "Agent"
        verbose_name_plural = "Agents"


class AgentCommissionTerm(BaseModel):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="commission_terms")

    # Term Details
    name = models.CharField(max_length=255, verbose_name="Term Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    # Conditions
    CONDITION_TYPES = [
        ("member_count", "Number of Members Registered"),
        ("beneficiary_count", "Number of Beneficiaries Registered"),
        ("premium_volume", "Total Premium Volume"),
        ("member_type", "Specific Member Type"),
        ("time_period", "Time Period Achievement"),
        ("retention_rate", "Member Retention Rate"),
    ]
    condition_type = models.CharField(max_length=20, choices=CONDITION_TYPES, verbose_name="Condition Type")

    # Condition Values
    threshold_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Threshold Value")
    member_types = models.CharField(max_length=50, blank=True, null=True, verbose_name="Applicable Member Types (comma-separated)")
    period_days = models.PositiveIntegerField(null=True, blank=True, verbose_name="Period in Days")

    # Rewards
    REWARD_TYPES = [
        ("percentage", "Percentage of Premium"),
        ("fixed_amount", "Fixed Amount"),
        ("tiered_rate", "Tiered Rate"),
        ("bonus", "One-time Bonus"),
    ]
    reward_type = models.CharField(max_length=15, choices=REWARD_TYPES, verbose_name="Reward Type")

    reward_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Reward Percentage")
    reward_fixed_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Fixed Reward Amount")

    # Term Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    effective_from = models.DateField(verbose_name="Effective From")
    effective_to = models.DateField(null=True, blank=True, verbose_name="Effective To")

    # Priority for overlapping terms
    priority = models.PositiveIntegerField(default=100, verbose_name="Priority")

    def __str__(self):
        return f"{self.agent.name} - {self.name}"

    class Meta:
        ordering = ["agent", "priority", "name"]
        verbose_name = "Agent Commission Term"
        verbose_name_plural = "Agent Commission Terms"


class AgentCommission(BaseModel):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="commissions")
    commission_term = models.ForeignKey(AgentCommissionTerm, on_delete=models.CASCADE, related_name="commissions", null=True, blank=True)

    # Commission Details
    commission_number = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Commission Number")

    # Source Information
    member = models.ForeignKey('configurations.Member', on_delete=models.CASCADE, related_name="agent_commissions", null=True, blank=True)

    COMMISSION_TYPES = [
        ("registration", "Member Registration"),
        ("renewal", "Member Renewal"),
        ("premium", "Premium Commission"),
        ("bonus", "Achievement Bonus"),
        ("override", "Override Commission"),
    ]
    commission_type = models.CharField(max_length=15, choices=COMMISSION_TYPES, verbose_name="Commission Type")

    # Amounts
    base_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,  verbose_name="Base Amount")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0,  verbose_name="Commission Rate %")
    commission_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Commission Amount")

    # Period
    period_from = models.DateField(verbose_name="Period From")
    period_to = models.DateField(verbose_name="Period To")

    # Status
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("C", "Calculated"),
        ("A", "Approved"),
        ("PD", "Paid"),
        ("H", "On Hold"),
        ("CN", "Cancelled"),
    ]
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default="P", verbose_name="Status")

    # Payment Details
    payment_date = models.DateField(null=True, blank=True, verbose_name="Payment Date")
    payment_reference = models.CharField(max_length=255, blank=True, null=True, verbose_name="Payment Reference")

    # Processing Details
    calculated_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="calculated_commissions", verbose_name="Calculated By")
    calculated_at = models.DateTimeField(null=True, blank=True, verbose_name="Calculated At")
    approved_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True,  related_name="approved_commissions", verbose_name="Approved By")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Approved At")


    def save(self, *args, **kwargs):
        if not self.commission_number:
            import datetime
            from sequences import Sequence
            date_str = datetime.datetime.now().strftime("%y%m")
            sequence_number = Sequence(f"commission_{date_str}").get_next_value()
            self.commission_number = f"COM{date_str}{sequence_number:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.commission_number} - {self.agent.name}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Agent Commission"
        verbose_name_plural = "Agent Commissions"
