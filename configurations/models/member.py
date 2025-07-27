from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from configurations.models.base_model import BaseModel
from configurations.models.currency import Currency
from configurations.models.package import Package


class MemberManager(models.Manager):
    def communities(self):
        return self.filter(type__in=["CO", "CM"])
    
    def valid_parents(self):
        """Return members that can be parents (Community, Family, Corporate)"""
        return self.filter(type__in=["CM", "FM", "CO"])
    
    def child_members(self):
        """Return members that can be children (Individual, HealthSave)"""
        return self.filter(type__in=["IN", "HS"])

class Member(BaseModel):
    name = models.CharField(max_length=255, unique=True, db_index=True, verbose_name="Member Name")

    MEMBER_TYPES = [
        ("CO", "Corporate"),  # 8-digit: 10xxxxxx
        ("CM", "Community"),  # 8-digit: 20xxxxxx
        ("HS", "HealthSave"),  # 8-digit: 30xxxxxx
        ("IN", "Individual"),  # 8-digit: 40xxxxxx
        ("FM", "Family"),  # 8-digit: 50xxxxxx
        # ("MF", "Microfinance"),  # 8-digit: 60xxxxxx
    ]
    type = models.CharField(max_length=2, choices=MEMBER_TYPES, verbose_name="Member Type")

    alias = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name="Alias")
    membership_number = models.CharField(max_length=10, unique=True, editable=False, db_index=True,
                                         verbose_name="Membership Number")
    logo = models.ImageField(max_length=255, upload_to="member/logo", null=True, blank=True, verbose_name="Logo")
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name="Main Currency")

    # Contact information
    address_line_1 = models.CharField(max_length=255, verbose_name="Address Line 1")
    address_line_2 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Address Line 2")
    address_line_3 = models.CharField(max_length=255, null=True, blank=True, verbose_name="Address Line 3")

    mobile = models.CharField(max_length=20, verbose_name="Mobile Number")
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telephone")
    email = models.EmailField(max_length=255, verbose_name="Email Address")

    # Business Rules
    signing_rule = models.CharField(max_length=1, choices=[("S", "Single"), ("D", "Dual"), ("A", "Any")], verbose_name="Signing Rule")
    status = models.CharField(max_length=1, default="A", choices=[("A", "Active"), ("I", "Inactive"), ("S", "Suspended")], verbose_name="Status")
    sponsor = models.CharField(max_length=1, choices=[("S", "Self"), ("E", "Employer"), ("G", "Government")],verbose_name="Sponsor")
    date_joined = models.DateField(auto_now_add=True, verbose_name="Date Joined")

    # Payment Configuration
    STOP_ORDER_CHOICES = [
        ("off", "Inactive"),
        ("per_day", "Per Day"),
        ("per_week", "Per Week"),
        ("per_month", "Per Month"),
    ]
    stop_order_form = models.CharField(max_length=10, choices=STOP_ORDER_CHOICES, default="off", verbose_name="Stop Order Cycle")
    stop_order_amount = models.DecimalField(decimal_places=2, max_digits=11, default=0, verbose_name="Stop Order Amount")
    stop_order_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Stop Order Number")

    # Organizational Structure (for Corporate members with iterative parent)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_members', verbose_name="Parent Organization")

    # Package and Verification
    default_package = models.ForeignKey('configurations.Package', on_delete=models.CASCADE, verbose_name="Default Package")
    kyc_verified_at = models.DateTimeField(blank=True, null=True, verbose_name="KYC Verified At")

    # Agent who registered this member
    registered_by = models.ForeignKey('Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name="registered_members", verbose_name="Registered By Agent")


    objects = MemberManager()

    def __str__(self):
        return f"{self.membership_number} - {self.name.upper()}"

    def clean(self):
        """
        Validate member hierarchy rules:
        - Only Community, Family, or Corporate members can have children
        - Individual or HealthSave members can only be children (must have a parent)
        """
        super().clean()
        
        # Check if this member can have children
        if hasattr(self, 'sub_members') and self.sub_members.exists():
            if self.type not in ['CM', 'FM', 'CO']:
                raise ValidationError({
                    'type': f'{self.get_type_display()} members cannot have child members. Only Community, Family, or Corporate members can have children.'
                })
        
        # Check if this member type can be a child
        if self.parent:
            if self.type not in ['IN', 'HS']:
                raise ValidationError({
                    'parent': f'{self.get_type_display()} members cannot be child members. Only Individual or HealthSave members can be children.'
                })
            
            # Ensure parent is of correct type
            if self.parent.type not in ['CM', 'FM', 'CO']:
                raise ValidationError({
                    'parent': f'Parent must be a Community, Family, or Corporate member. {self.parent.get_type_display()} cannot be a parent.'
                })
        # else:
        #     # If no parent, Individual and HealthSave members should have a parent
        #     if self.type in ['IN', 'HS']:
        #         raise ValidationError({
        #             'parent': f'{self.get_type_display()} members must have a parent. Only Community, Family, or Corporate members can be standalone.'
        #         })

    def save(self, *args, **kwargs):
        # Run validation before saving
        self.clean()
        
        if self.stop_order_form == "off":
            self.stop_order_amount = 0
            self.stop_order_number = None

        if not self.membership_number:

            if self.parent:
                # Sub-member inherits prefix from parent and gets sequential number
                parent_prefix = self.parent.membership_number[:8]  # First 4 digits
                from sequences import Sequence
                sequence_number = Sequence(f'sub_member_{parent_prefix}').get_next_value()
                self.membership_number = f"{parent_prefix}{sequence_number:02d}"

                print("self.membership_number", self.membership_number)
            else:
                # Generate new membership number based on type
                type_prefixes = {
                    "CO": "10",  # Corporate
                    "CM": "20",  # Community
                    "HS": "30",  # HealthSave
                    "IN": "40",  # Individual
                    "FM": "50",  # Family
                    "MF": "60",  # Microfinance
                }
                today = timezone.now().date()
                date_prefix = today.strftime("%y")+ today.strftime("%m")[1]

                prefix = type_prefixes.get(self.type, "99")
                from sequences import Sequence
                sequence_number = Sequence(f'member_number_{self.type}_{date_prefix}').get_next_value()
                self.membership_number = f"{prefix}{date_prefix}{sequence_number:03d}00"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["membership_number"]
        verbose_name = "Member"
        verbose_name_plural = "Members"


class MemberKYCRequirement(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Requirement Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    # Requirement Type
    REQUIREMENT_TYPES = [
        ("document", "Document Upload"),
        ("verification", "Identity Verification"),
        ("information", "Information Provision"),
        ("declaration", "Declaration/Consent"),
    ]
    requirement_type = models.CharField(max_length=15, choices=REQUIREMENT_TYPES,
                                        verbose_name="Requirement Type")

    # Applicability
    member_types = models.CharField(max_length=50, blank=True, null=True,
                                    verbose_name="Applicable Member Types (comma-separated)")
    is_mandatory = models.BooleanField(default=True, verbose_name="Is Mandatory")

    # Document specific fields
    accepted_file_types = models.CharField(max_length=255, blank=True, null=True,
                                           verbose_name="Accepted File Types")
    max_file_size_mb = models.PositiveIntegerField(default=5, verbose_name="Max File Size (MB)")
    has_expiry = models.BooleanField(default=False, verbose_name="Has Expiry Date")

    # Verification
    requires_manual_verification = models.BooleanField(default=False,
                                                       verbose_name="Requires Manual Verification")
    auto_verify_conditions = models.TextField(blank=True, null=True,
                                              verbose_name="Auto Verification Conditions")

    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    sort_order = models.PositiveIntegerField(default=100, verbose_name="Sort Order")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Member KYC Requirement"
        verbose_name_plural = "Member KYC Requirements"


class MemberKYCDocument(BaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="kyc_documents")
    requirement = models.ForeignKey(MemberKYCRequirement, on_delete=models.CASCADE,
                                    related_name="member_documents")

    # Document Details
    document_file = models.FileField(upload_to="member/kyc/", verbose_name="Document File")
    document_number = models.CharField(max_length=255, blank=True, null=True,
                                       verbose_name="Document Number")
    issue_date = models.DateField(null=True, blank=True, verbose_name="Issue Date")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Expiry Date")
    issuing_authority = models.CharField(max_length=255, blank=True, null=True,
                                         verbose_name="Issuing Authority")

    # Status
    STATUS_CHOICES = [
        ("P", "Pending"),
        ("V", "Verified"),
        ("R", "Rejected"),
        ("E", "Expired"),
    ]
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P", verbose_name="Status")

    # Verification Details
    verified_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name="Verified By")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Verified At")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="Rejection Reason")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")

    @property
    def is_expired(self):
        if self.expiry_date:
            from django.utils import timezone
            return self.expiry_date < timezone.now().date()
        return False

    def __str__(self):
        return f"{self.member.name} - {self.requirement.name}"

    class Meta:
        unique_together = [("member", "requirement")]
        ordering = ["member", "requirement"]
        verbose_name = "Member KYC Document"
        verbose_name_plural = "Member KYC Documents"
