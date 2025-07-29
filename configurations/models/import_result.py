from django.contrib.auth import get_user_model
from django.db import models
import uuid

User = get_user_model()

class ImportResult(models.Model):
    """Model to track import operations and their results"""
    
    IMPORT_TYPES = [
        ('member', 'Member'),
        ('beneficiary', 'Beneficiary'),
        ('claim', 'Claim'),
        ('service_provider', 'Service Provider'),
        ('service', 'Service'),
        ('agent', 'Agent'),
        ('currency', 'Currency'),
        ('tier', 'Tier'),
        ('package', 'Package'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    # Import metadata
    import_type = models.CharField(max_length=20, choices=IMPORT_TYPES, verbose_name='Import Type')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Imported By')
    
    # File information
    original_filename = models.CharField(max_length=255, verbose_name='Original Filename')
    file_format = models.CharField(max_length=10, verbose_name='File Format')  # csv, xlsx, etc.
    file_size = models.PositiveIntegerField(verbose_name='File Size (bytes)')
    
    # Import statistics
    total_rows = models.PositiveIntegerField(default=0, verbose_name='Total Rows')
    successful_rows = models.PositiveIntegerField(default=0, verbose_name='Successful Rows')
    failed_rows = models.PositiveIntegerField(default=0, verbose_name='Failed Rows')
    skipped_rows = models.PositiveIntegerField(default=0, verbose_name='Skipped Rows')
    
    # Processing times
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Started At')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completed At')
    
    # Import options (from form)
    import_options = models.JSONField(default=dict, verbose_name='Import Options')
    
    # Summary and notes
    summary = models.TextField(blank=True, verbose_name='Import Summary')
    notes = models.TextField(blank=True, verbose_name='Additional Notes')
    
    def __str__(self):
        return f"{self.get_import_type_display()} Import - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_rows == 0:
            return 0
        return round((self.successful_rows / self.total_rows) * 100, 2)
    
    @property
    def duration(self):
        """Calculate import duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def has_errors(self):
        """Check if import has any errors"""
        return self.failed_rows > 0 or self.import_errors.exists()
    
    class Meta:
        verbose_name = 'Import Result'
        verbose_name_plural = 'Import Results'
        ordering = ['-created_at']


class ImportError(models.Model):
    """Model to store detailed import errors"""
    
    ERROR_TYPES = [
        ('validation', 'Validation Error'),
        ('duplicate', 'Duplicate Entry'),
        ('missing_data', 'Missing Required Data'),
        ('invalid_format', 'Invalid Format'),
        ('foreign_key', 'Foreign Key Error'),
        ('business_rule', 'Business Rule Violation'),
        ('system', 'System Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_result = models.ForeignKey(ImportResult, on_delete=models.CASCADE, related_name='import_errors')
    
    # Error details
    row_number = models.PositiveIntegerField(verbose_name='Row Number')
    error_type = models.CharField(max_length=20, choices=ERROR_TYPES, verbose_name='Error Type')
    field_name = models.CharField(max_length=100, blank=True, verbose_name='Field Name')
    error_message = models.TextField(verbose_name='Error Message')
    
    # Row data for reference
    row_data = models.JSONField(default=dict, verbose_name='Row Data')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    def __str__(self):
        return f"Row {self.row_number}: {self.error_message[:50]}..."
    
    class Meta:
        verbose_name = 'Import Error'
        verbose_name_plural = 'Import Errors'
        ordering = ['row_number']


class ImportSuccess(models.Model):
    """Model to store successfully imported records for reference"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_result = models.ForeignKey(ImportResult, on_delete=models.CASCADE, related_name='import_successes')
    
    # Success details
    row_number = models.PositiveIntegerField(verbose_name='Row Number')
    object_id = models.CharField(max_length=100, verbose_name='Created Object ID')
    object_repr = models.CharField(max_length=255, verbose_name='Object Representation')
    
    # Row data for reference
    row_data = models.JSONField(default=dict, verbose_name='Row Data')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    def __str__(self):
        return f"Row {self.row_number}: {self.object_repr}"
    
    class Meta:
        verbose_name = 'Import Success'
        verbose_name_plural = 'Import Successes'
        ordering = ['row_number']