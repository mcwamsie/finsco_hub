from django.db import models

from configurations.models.base_model import BaseModel


class AdjudicationRule(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Rule Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    # Rule Conditions
    RULE_TYPES = [
        ('C', 'Claim'),
        ('SR', 'Service Request'),
        ('B', 'Both'),
    ]
    rule_type = models.CharField(max_length=2, choices=RULE_TYPES, default='B', verbose_name="Rule Type")

    # Service-based conditions
    services = models.ManyToManyField('configurations.Service', blank=True, verbose_name="Services")
    service_provider_type = models.ManyToManyField('configurations.ServiceProviderType', blank=True,
                                        verbose_name="Categories")

    # Amount-based conditions
    min_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                     verbose_name="Minimum Amount")
    max_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                     verbose_name="Maximum Amount")

    # Beneficiary-based conditions
    BENEFICIARY_TYPES = [
        ('P', 'Principal'),
        ('S', 'Spouse'),
        ('D', 'Dependent'),
        ('E', 'Employee'),
        ('A', 'All'),
    ]
    beneficiary_type = models.CharField(max_length=1, choices=BENEFICIARY_TYPES, default='A',
                                        verbose_name="Beneficiary Type")

    # Member type conditions
    member_types = models.CharField(max_length=50, blank=True, null=True,
                                    verbose_name="Member Types (comma-separated)")

    # Provider tier conditions
    provider_tiers = models.ManyToManyField('configurations.Tier', blank=True, verbose_name="Provider Tiers")

    # Time-based conditions
    max_days_from_service = models.PositiveIntegerField(default=0,
                                                        verbose_name="Max Days from Service")

    # Frequency conditions
    max_visits_per_year = models.PositiveIntegerField(default=0,
                                                      verbose_name="Max Visits Per Year")
    max_visits_per_month = models.PositiveIntegerField(default=0,
                                                       verbose_name="Max Visits Per Month")

    # Age-based conditions
    min_age = models.PositiveIntegerField(default=0, verbose_name="Minimum Age")
    max_age = models.PositiveIntegerField(default=0, verbose_name="Maximum Age")

    # Special conditions
    requires_referral = models.BooleanField(default=False, verbose_name="Requires Referral")
    requires_prior_auth = models.BooleanField(default=False, verbose_name="Requires Prior Authorization")
    requires_supporting_docs = models.BooleanField(default=False, verbose_name="Requires Supporting Documents")
    chronic_condition_only = models.BooleanField(default=False, verbose_name="Chronic Condition Only")
    wellness_visit_only = models.BooleanField(default=False, verbose_name="Wellness Visit Only")

    # Actions
    ACTION_CHOICES = [
        ('AUTO_APPROVE', 'Auto Approve'),
        ('AUTO_DECLINE', 'Auto Decline'),
        ('MANUAL_REVIEW', 'Manual Review'),
        ('CLINICAL_REVIEW', 'Clinical Review'),
        ('REDUCE_AMOUNT', 'Reduce Amount'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='AUTO_APPROVE',
                              verbose_name="Action")

    # Reduction settings
    reduction_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                               verbose_name="Reduction Percentage")
    reduction_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                           verbose_name="Reduction Amount")

    # Co-payment settings
    co_payment_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                                verbose_name="Co-payment Percentage")
    co_payment_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                            verbose_name="Co-payment Amount")

    # Rule priority and status
    priority = models.PositiveIntegerField(default=100, verbose_name="Priority")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    # Effective dates
    effective_from = models.DateField(verbose_name="Effective From")
    effective_to = models.DateField(null=True, blank=True, verbose_name="Effective To")

    def __str__(self):
        return f"{self.name} ({self.get_action_display()})"

    class Meta:
        ordering = ['priority', 'name']
        verbose_name = "Adjudication Rule"
        verbose_name_plural = "Adjudication Rules"


class AdjudicationMessageCode(BaseModel):
    code = models.CharField(max_length=10, unique=True, verbose_name="Message Code")
    title = models.CharField(max_length=255, verbose_name="Message Title")
    description = models.TextField(verbose_name="Message Description")

    MESSAGE_TYPES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('APPROVAL', 'Approval'),
        ('DECLINE', 'Decline'),
    ]
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, verbose_name="Message Type")

    # Visibility
    is_visible_to_provider = models.BooleanField(default=True, verbose_name="Visible to Provider")
    is_visible_to_member = models.BooleanField(default=False, verbose_name="Visible to Member")

    # Category for grouping
    category = models.CharField(max_length=50, blank=True, null=True, verbose_name="Category")

    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    def __str__(self):
        return f"{self.code}: {self.title}"

    class Meta:
        ordering = ['category', 'code']
        verbose_name = "Adjudication Message Code"
        verbose_name_plural = "Adjudication Message Codes"


class AdjudicationResult(BaseModel):
    # Link to original request/claim
    claim = models.ForeignKey('Claim', on_delete=models.CASCADE, null=True, blank=True,
                              related_name='adjudication_results')
    service_request = models.ForeignKey('ServiceRequest', on_delete=models.CASCADE, null=True, blank=True,
                                        related_name='adjudication_results')

    # Adjudication details
    RESULT_CHOICES = [
        ('APPROVED', 'Approved'),
        ('PARTIALLY_APPROVED', 'Partially Approved'),
        ('DECLINED', 'Declined'),
        ('PENDING_REVIEW', 'Pending Review'),
        ('PENDING_CLINICAL', 'Pending Clinical Review'),
        ('PENDING_DOCS', 'Pending Documentation'),
    ]
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, verbose_name="Result")

    # Original and adjudicated amounts
    original_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                          verbose_name="Original Amount")
    adjudicated_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                             verbose_name="Adjudicated Amount")
    co_payment_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                            verbose_name="Co-payment Amount")

    # Rules applied
    rules_applied = models.ManyToManyField(AdjudicationRule, through='AdjudicationRuleApplication',
                                           verbose_name="Rules Applied")

    # Processing details
    PROCESSING_TYPE_CHOICES = [
        ('AUTOMATIC', 'Automatic'),
        ('MANUAL', 'Manual'),
        ('CLINICAL', 'Clinical Review'),
    ]
    processing_type = models.CharField(max_length=10, choices=PROCESSING_TYPE_CHOICES, default='AUTOMATIC',
                                       verbose_name="Processing Type")

    processed_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='adjudicated_claims', verbose_name="Processed By")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Processed At")

    # Review details
    review_notes = models.TextField(blank=True, null=True, verbose_name="Review Notes")
    decline_reason = models.TextField(blank=True, null=True, verbose_name="Decline Reason")

    # System flags
    requires_manual_review = models.BooleanField(default=False, verbose_name="Requires Manual Review")
    requires_clinical_review = models.BooleanField(default=False, verbose_name="Requires Clinical Review")
    requires_documentation = models.BooleanField(default=False, verbose_name="Requires Documentation")
    is_fraud_suspected = models.BooleanField(default=False, verbose_name="Fraud Suspected")

    def __str__(self):
        entity = self.claim or self.service_request
        return f"Adjudication: {entity} - {self.get_result_display()}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Adjudication Result"
        verbose_name_plural = "Adjudication Results"


class AdjudicationRuleApplication(BaseModel):
    adjudication_result = models.ForeignKey(AdjudicationResult, on_delete=models.CASCADE,
                                            verbose_name="Adjudication Result")
    rule = models.ForeignKey(AdjudicationRule, on_delete=models.CASCADE, verbose_name="Rule")

    # Rule application details
    was_triggered = models.BooleanField(default=False, verbose_name="Was Triggered")
    conditions_met = models.JSONField(default=dict, verbose_name="Conditions Met")
    amount_before = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                        verbose_name="Amount Before")
    amount_after = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                       verbose_name="Amount After")

    def __str__(self):
        return f"{self.rule.name} - {'Applied' if self.was_triggered else 'Not Applied'}"

    class Meta:
        verbose_name = "Rule Application"
        verbose_name_plural = "Rule Applications"


class AdjudicationMessage(BaseModel):
    adjudication_result = models.ForeignKey(AdjudicationResult, on_delete=models.CASCADE,
                                            related_name='messages', verbose_name="Adjudication Result")
    message_code = models.ForeignKey(AdjudicationMessageCode, on_delete=models.CASCADE,
                                     related_name='adjudication_messages', verbose_name="Message Code")

    # Custom message details (can override code defaults)
    custom_title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Custom Title")
    custom_description = models.TextField(blank=True, null=True, verbose_name="Custom Description")

    # Context data
    context_data = models.JSONField(default=dict, verbose_name="Context Data")

    # Message sequence
    sequence_number = models.PositiveIntegerField(default=1, verbose_name="Sequence Number")

    @property
    def title(self):
        return self.custom_title or self.message_code.title

    @property
    def description(self):
        return self.custom_description or self.message_code.description

    @property
    def message_type(self):
        return self.message_code.message_type

    def __str__(self):
        return f"{self.message_code.code}: {self.title}"

    class Meta:
        ordering = ['adjudication_result', 'sequence_number']
        verbose_name = "Adjudication Message"
        verbose_name_plural = "Adjudication Messages"

