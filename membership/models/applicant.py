import random
import re
import string
from datetime import datetime, date

from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from sequences import Sequence

from authentication.models import User
from configurations.models import Bank, RegisteredApplication
from configurations.models.base_model import BaseModel
from fisco_hub_8d import settings

# Choices for some fields
GENDER_CHOICES = [
    ('Male', 'Male'),
    ('Female', 'Female'),
    # ('Other', 'Other'),
]

TITLE_CHOICES = [
    ('', 'Unknown'),
    ('Mr.', 'Mr.'),
    ('Ms.', 'Ms.'),
    ('Mrs.', 'Mrs.'),
    ('Dr.', 'Dr.'),
]

MARITAL_STATUS_CHOICES = [
    ('', 'Unknown'),
    ('Single', 'Single'),
    ('Married', 'Married'),
    ('Divorced', 'Divorced'),
    ('Widowed', 'Widowed'),
]

STATUS_CHOICES = [
    ('Approved', 'Approved'),
    ('Disapproved', 'Rejected'),
    ('Pending', 'Pending'),
]


def validate_future_date(value):
    print('validate_future_date called')
    if isinstance(value, datetime):
        value = value.date()
    if value > date.today():
        raise ValidationError('The date must not be in the future.')


def validate_national_id(value):
    if not value:
        raise ValidationError("National ID cannot be empty.")
    value = clean_number(value)
    if not re.match(r'^[0-9]{2}[0-9]{6,7}[A-Z][0-9][0-9]$', value):
        raise ValidationError("Not a valid National ID.")

    if ApplicantMember.objects.filter(national_id=value).exists():
        raise ValidationError("This National ID is already taken.")


# def validate_national_id(value, model=None, field_name='national_id'):
#     if not value:
#         raise ValidationError("National ID cannot be empty.")
#     value = clean_number(value)
#     if not re.match(r'^[0-9]{2}[0-9]{6,7}[A-Z][0-9][0-9]$', value):
#         raise ValidationError("Not a valid National ID.")
#     if model and model.objects.filter(**{field_name: value}).exists():
#         raise ValidationError("This National ID is already taken.")

def validate_beneficiary_national_id(value):
    print('validate_beneficiary_national_id called')

    if value:
        value = clean_number(value)
        if not re.match(r'^[0-9]{2}[0-9]{6,7}[A-Z][0-9][0-9]$', value):
            raise ValidationError("Not a valid National ID.")

        if ApplicantBeneficiary.objects.filter(id_number=value).exists():
            raise ValidationError("This National ID is already taken.")


def validate_image_file(value):
    if not value.name.endswith(('.jpg', '.jpeg', '.png')):
        raise ValidationError("Only JPEG and PNG files are allowed.")


def get_application_number():
    date = timezone.now().today().strftime("%d%m%y")
    sequence_number = Sequence(date).get_next_value()
    random_letter = random.choice(string.ascii_uppercase)
    return f"{date}{sequence_number}{random_letter}"


class ApplicantMember(BaseModel):
    # Personal Information
    application_number = models.CharField(max_length=50, unique=True, default=get_application_number)
    title = models.CharField(max_length=10, blank=True, null=True, default="", choices=TITLE_CHOICES)
    ethnic_group = models.CharField(max_length=50, blank=True, null=True)
    surname = models.CharField(max_length=100)
    firstname = models.CharField(max_length=100)
    marital_status = models.CharField(max_length=10, blank=True, null=True, default="", choices=MARITAL_STATUS_CHOICES)
    date_of_birth = models.DateField(validators=[validate_future_date])
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    national_id = models.CharField(max_length=20, unique=True, validators=[validate_national_id])

    # Contact Information
    cell_number = PhoneNumberField(unique=True)
    telephone_number = PhoneNumberField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # Address Information
    physical_address = models.CharField(max_length=255, blank=True, null=True)
    postal_address = models.CharField(max_length=255, blank=True, null=True)
    country_of_residence = models.CharField(max_length=100)

    # Banking Information
    bank_name = models.ForeignKey(Bank, blank=True, null=True, related_name='member_applicants',
                                  on_delete=models.CASCADE)
    branch_name = models.CharField(max_length=100, blank=True, null=True, )
    branch_code = models.CharField(max_length=50, blank=True, null=True, )
    bank_account_number = models.CharField(max_length=50, blank=True, null=True, )
    member_is_a_beneficiary = models.BooleanField(default=False)
    status = models.CharField(max_length=11, default='Pending', choices=STATUS_CHOICES)

    # Subscription Details
    # monthly_top_up_amount = models.DecimalField(max_digits=10, decimal_places=2)
    application = models.ForeignKey(
        RegisteredApplication,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='members'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    selfie_photo = models.FileField(upload_to='applicants/selfies/', blank=False, null=True,
                                    verbose_name="Selfie Photo")
    national_id_photo = models.FileField(upload_to='applicants/national_id/', blank=False, null=True,
                                         verbose_name="National ID/Passport Photo")

    def save(self, *args, **kwargs):
        self.national_id = clean_number(self.national_id)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} {self.firstname} {self.surname}"

    class Meta:
        verbose_name = 'Applicant Member'
        verbose_name_plural = 'Applicant Members'
        ordering = ('-status', 'created_at')
        constraints = [
            models.UniqueConstraint(fields=['national_id'], name='unique_national_id'),
            models.UniqueConstraint(fields=['cell_number'], name='unique_cell_number'),
        ]


class ApplicantBeneficiary(models.Model):
    member = models.ForeignKey(ApplicantMember, related_name='beneficiaries', on_delete=models.CASCADE)
    firstname = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    date_of_birth = models.DateField(validators=[validate_future_date])
    contact = PhoneNumberField(verbose_name="Contact Number", null=True, blank=True)
    id_number = models.CharField(max_length=20, validators=[validate_beneficiary_national_id], null=True, blank=True)
    sex = models.CharField(max_length=10, choices=GENDER_CHOICES)

    selfie_photo = models.FileField(upload_to='applicants-beneficiary/selfies/', blank=False, null=True,
                                    verbose_name="Selfie Photo")
    national_id_photo = models.FileField(upload_to='applicants-beneficiary/national_id/', blank=False, null=True,
                                         verbose_name="National ID/Passport Photo")

    def save(self, *args, **kwargs):
        self.id_number = clean_number(self.id_number) if self.id_number else None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.firstname} {self.surname} ({self.relationship})"


class ApplicationMessage(BaseModel):
    applicant = models.ForeignKey("ApplicantMember", on_delete=models.CASCADE, related_name="messages")
    CHANNEL_CHOICES = [
        ("SMS", 'SMS'),
        ("EMAIL", 'Email'),
        ("WHATSAPP", 'Whatsapp'),
    ]
    channel = models.CharField(max_length=255, choices=CHANNEL_CHOICES)
    message = models.TextField(blank=True)


def send_registration_alert(member: ApplicantMember):
    # print("sending email to", member)
    """
    Sends an email notification to the admin when a new member registers.
    """
    subject = "New Member Registration"
    message = f"""
    A new member has registered.

    Name: {member.firstname} {member.surname}
    Email: {member.email}
    Phone: {member.cell_number}
    Application: {member.application.name if member.application else 'N/A'}

    Please log in to the admin dashboard for more details.
    """
    recipient_list = [user.email for user in User.objects.filter(is_active=True, preferred_notification_method="EMAIL", notify_applications=True)]


    if hasattr(settings, 'MEMBER_APPLICATION_EMAIL'):
        recipient_list.append(settings.MEMBER_APPLICATION_EMAIL)

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False
    )


def clean_number(value: str):
    return (value.strip()
            .replace("-", "")
            .replace("_", "")
            .replace("/", "")
            .replace(" ", "")
            .upper())
