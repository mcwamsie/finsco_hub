from decimal import Decimal

from django.db import models

from configurations.models.base_model import BaseModel


class Beneficiary(BaseModel):
    # Personal Information
    first_name = models.CharField(max_length=255, verbose_name="First Name")
    last_name = models.CharField(max_length=255, verbose_name="Last Name")
    middle_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Middle Name")
    national_id_number = models.CharField(max_length=255, unique=True, verbose_name="National ID Number")
    date_of_birth = models.DateField(verbose_name="Date of Birth")

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Gender")
    
    # Profile Photo
    photo = models.ImageField(upload_to='beneficiary/photos/', blank=True, null=True, verbose_name="Profile Photo")

    # Contact Information
    mobile = models.CharField(max_length=20, blank=True, null=True, verbose_name="Mobile Number")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email Address")

    # Physical Address
    physical_address = models.TextField(blank=True, null=True, verbose_name="Physical Address")

    # Medical Aid Information
    member = models.ForeignKey('configurations.Member', on_delete=models.CASCADE, related_name="beneficiaries",  verbose_name="Member")
    membership_number = models.CharField(max_length=10, editable=False, verbose_name="Membership Number")
    dependent_code = models.CharField(max_length=3, editable=False, verbose_name="Dependent Code")

    # Relationship and Status
    relationship = models.CharField(max_length=255, null=True, blank=True, verbose_name="Relationship")

    STATUS_CHOICES = [
        ("A", "Active"),
        ("S", "Suspended"),
        ("T", "Terminated")
    ]
    status = models.CharField(max_length=1, default="A", choices=STATUS_CHOICES, verbose_name="Status")

    TYPE_CHOICES = [
        ("P", "Principal"),  # Main member
        ("S", "Spouse"),  # Spouse
        ("D", "Dependent"),  # Child/Dependent
        ("E", "Employee"),  # For corporate members
    ]
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, verbose_name="Type")

    # Package and Limits
    # package = models.ForeignKey('configurations.Package', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Benefit Package")
    # annual_limit = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Annual Limit")

    # Important Dates
    date_joined = models.DateField(auto_now_add=True, verbose_name="Date Joined")
    benefit_start_date = models.DateField(null=True, blank=True, verbose_name="Benefit Start Date")
    suspension_start_date = models.DateField(null=True, blank=True, verbose_name="Suspension Start Date")
    suspension_end_date = models.DateField(null=True, blank=True, verbose_name="Suspension End Date")
    termination_date = models.DateField(null=True, blank=True, verbose_name="Termination Date")

    # Principal Member Link (for dependents)
    principal = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True,  related_name="dependents", verbose_name="Principal Member")

    # Other identification
    other_identity_number = models.CharField(max_length=255, null=True, blank=True, verbose_name="Other Identity Number")

    def __str__(self):
        return f"{self.membership_number}/{self.dependent_code}: {self.first_name} {self.last_name}"

    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def package(self):
        """
        Returns the beneficiary's package. If not set, inherits from member's default package.
        """
        if self.member and self.member.default_package:
            return self.member.default_package
        return None

    @package.setter
    def package(self, value):
        """
        Sets the beneficiary's package.
        """
        self._package = value

    @property
    def annual_limit(self):
        """
        Returns the beneficiary's annual limit. If not set or 0, inherits from package.
        """
        if self.member and self.member.default_package.global_annual_limit > 0:
            return self.member.default_package.global_annual_limit
        return Decimal('0.00')

    @annual_limit.setter
    def annual_limit(self, value):
        """
        Sets the beneficiary's annual limit.
        """
        self._annual_limit = value

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        # Set membership number from member
        self.membership_number = self.member.membership_number

        # Generate dependent code if not set
        if not self.dependent_code:
            if self.type == "P":  # Principal member
                self.dependent_code = "000"
            else:
                # Generate next dependent code for this member
                last_dependent = Beneficiary.objects.filter(
                    member=self.member
                ).exclude(type="P").order_by("-dependent_code").first()

                if last_dependent and last_dependent.dependent_code.isdigit():
                    next_code = int(last_dependent.dependent_code) + 1
                    self.dependent_code = f"{next_code:03d}"
                else:
                    self.dependent_code = "001"

        # Set principal if this is a dependent
        if self.type in ["S", "D", "E"] and not self.principal:
            principal_member = Beneficiary.objects.filter(
                member=self.member, type="P"
            ).first()
            if principal_member:
                self.principal = principal_member

        # Inherit package from member if not set
        if not self._package and self.member.default_package:
            self._package = self.member.default_package

        super().save(force_insert, force_update)

    class Meta:
        verbose_name_plural = "Beneficiaries"
        verbose_name = "Beneficiary"
        ordering = ["membership_number", "dependent_code"]
        unique_together = [("member", "national_id_number"), ("membership_number", "dependent_code")]
