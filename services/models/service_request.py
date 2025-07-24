from django.db import models

from configurations.models.base_model import BaseModel


class ServiceRequest(BaseModel):
    request_number = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Request Number")

    # Patient Information
    beneficiary = models.ForeignKey('membership.Beneficiary', on_delete=models.CASCADE, related_name="service_requests", verbose_name="Beneficiary")

    # Provider Information
    service_provider = models.ForeignKey('configurations.ServiceProvider', on_delete=models.CASCADE, related_name="service_requests", verbose_name="Service Provider")
    referring_provider = models.ForeignKey('configurations.ServiceProvider', on_delete=models.SET_NULL, null=True, blank=True, related_name="referred_service_requests", verbose_name="Referring Provider")

    # Request Details
    PRIORITY_CHOICES = [
        ("R", "Routine"),
        ("U", "Urgent"),
        ("E", "Emergency"),
    ]
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default="R", verbose_name="Priority")

    APPROVAL_TYPE_CHOICES = [
        ("A", "Automatic"),
        ("M", "Manual"),
        ("C", "Clinical"),
    ]
    approval_type = models.CharField(max_length=1, choices=APPROVAL_TYPE_CHOICES, default="A", verbose_name="Approval Type")

    # Medical Information
    chief_complaint = models.TextField(verbose_name="Chief Complaint")
    clinical_history = models.TextField(blank=True, null=True, verbose_name="Clinical History")
    planned_treatment = models.TextField(verbose_name="Planned Treatment")

    # Financial Information
    estimated_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Estimated Amount")
    approved_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Approved Amount")

    # Dates
    requested_date = models.DateField(auto_now_add=True, verbose_name="Requested Date")
    proposed_service_date = models.DateField(verbose_name="Proposed Service Date")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Authorization Expiry")

    # Status and Workflow
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("U", "Under Review"),
        ("A", "Approved"),
        ("PA", "Partially Approved"),
        ("D", "Declined"),
        ("E", "Expired"),
        ("C", "Cancelled"),
        ("UT", "Utilized"),
    ]
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default="P", verbose_name="Status")

    # Approval Workflow
    requested_by = models.ForeignKey('authentication.User', on_delete=models.CASCADE,  related_name="service_requests", verbose_name="Requested By")
    reviewed_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_service_requests", verbose_name="Reviewed By")
    approved_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_service_requests", verbose_name="Approved By")

    # Review Details
    review_date = models.DateTimeField(null=True, blank=True, verbose_name="Review Date")
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name="Approval Date")
    review_notes = models.TextField(blank=True, null=True, verbose_name="Review Notes")
    decline_reason = models.TextField(blank=True, null=True, verbose_name="Decline Reason")

    # Supporting Documents
    supporting_document_1 = models.FileField(upload_to="service_requests/", blank=True, null=True, verbose_name="Supporting Document 1")
    supporting_document_2 = models.FileField(upload_to="service_requests/", blank=True, null=True, verbose_name="Supporting Document 2")
    supporting_document_3 = models.FileField(upload_to="service_requests/", blank=True, null=True, verbose_name="Supporting Document 3")

    # Authorization Details
    authorization_code = models.CharField(max_length=20, blank=True, null=True, unique=True, verbose_name="Authorization Code")

    # Utilization Tracking
    utilization_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Utilized Amount")
    remaining_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Remaining Amount")

    def save(self, *args, **kwargs):
        if not self.request_number:
            import datetime
            from sequences import Sequence
            date_number = datetime.datetime.now().strftime("%y%m%d")
            sequence_number = Sequence(f"service-request-{date_number}").get_next_value()
            self.request_number = f"SR{date_number}{sequence_number:04d}"

        # Generate authorization code for approved requests
        if self.status == "A" and not self.authorization_code:
            from sequences import Sequence
            sequence_number = Sequence("authorization_code").get_next_value()
            self.authorization_code = f"AUTH{sequence_number:06d}"

        # Calculate remaining amount
        self.remaining_amount = max(0, self.approved_amount - self.utilization_amount)

        # Set expiry date if approved (default 30 days)
        if self.status == "A" and not self.expiry_date:
            from datetime import timedelta
            self.expiry_date = self.proposed_service_date + timedelta(days=30)

        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        if self.expiry_date and self.status == "A":
            import datetime
            return datetime.date.today() > self.expiry_date
        return False

    @property
    def can_be_utilized(self):
        return (self.status == "A" and
                not self.is_expired and
                self.remaining_amount > 0)

    def __str__(self):
        return f"{self.request_number} - {self.beneficiary}"

    class Meta:
        ordering = ["-requested_date", "-created_at"]
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"


class ServiceRequestItem(BaseModel):
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE,  related_name="items", verbose_name="Service Request")
    service = models.ForeignKey('configurations.Service', on_delete=models.CASCADE, related_name="request_items")

    # Item Details
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name="Quantity")
    unit_price = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Unit Price")
    estimated_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Estimated Amount")
    approved_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Approved Amount")

    # Clinical Information
    clinical_justification = models.TextField(blank=True, null=True, verbose_name="Clinical Justification")

    # Approval Details
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("A", "Approved"),
        ("PA", "Partially Approved"),
        ("D", "Declined"),
    ]
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default="P", verbose_name="Status")
    decline_reason = models.TextField(blank=True, null=True, verbose_name="Decline Reason")

    # Utilization
    utilization_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Utilization Quantity")
    utilization_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Utilization Amount")

    def save(self, *args, **kwargs):
        # Calculate estimated amount
        self.estimated_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service_request.request_number} - {self.service.description}"

    class Meta:
        ordering = ["service__code"]
        verbose_name = "Service Request Item"
        verbose_name_plural = "Service Request Items"
