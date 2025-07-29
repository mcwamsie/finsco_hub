from django.utils import timezone
from configurations.models import ImportResult, ImportError, ImportSuccess
import os


class ImportResultTracker:
    """Utility class to track import operations and their results"""
    
    def __init__(self, import_type, user, file_obj, import_options=None):
        self.import_type = import_type
        self.user = user
        self.file_obj = file_obj
        self.import_options = import_options or {}
        self.import_result = None
        
    def start_import(self):
        """Initialize the import result record"""
        file_size = 0
        if hasattr(self.file_obj, 'size'):
            file_size = self.file_obj.size
        elif hasattr(self.file_obj, 'seek') and hasattr(self.file_obj, 'tell'):
            # For file-like objects
            current_pos = self.file_obj.tell()
            self.file_obj.seek(0, 2)  # Seek to end
            file_size = self.file_obj.tell()
            self.file_obj.seek(current_pos)  # Restore position
        
        file_format = 'unknown'
        filename = getattr(self.file_obj, 'name', 'unknown')
        if filename:
            _, ext = os.path.splitext(filename)
            file_format = ext.lower().lstrip('.')
        
        self.import_result = ImportResult.objects.create(
            import_type=self.import_type,
            status='processing',
            user=self.user,
            original_filename=filename,
            file_format=file_format,
            file_size=file_size,
            import_options=self.import_options,
            started_at=timezone.now()
        )
        return self.import_result
    
    def update_totals(self, total_rows, successful_rows=0, failed_rows=0, skipped_rows=0):
        """Update the import statistics"""
        if self.import_result:
            self.import_result.total_rows = total_rows
            self.import_result.successful_rows = successful_rows
            self.import_result.failed_rows = failed_rows
            self.import_result.skipped_rows = skipped_rows
            self.import_result.save()
    
    def add_error(self, row_number, error_type, error_message, field_name='', row_data=None):
        """Add an error record"""
        if self.import_result:
            ImportError.objects.create(
                import_result=self.import_result,
                row_number=row_number,
                error_type=error_type,
                field_name=field_name,
                error_message=error_message,
                row_data=row_data or {}
            )
    
    def add_success(self, row_number, created_object, row_data=None):
        """Add a success record"""
        if self.import_result:
            ImportSuccess.objects.create(
                import_result=self.import_result,
                row_number=row_number,
                object_id=str(created_object.pk),
                object_repr=str(created_object),
                row_data=row_data or {}
            )
    
    def complete_import(self, status='completed', summary='', notes=''):
        """Mark the import as completed"""
        if self.import_result:
            self.import_result.status = status
            self.import_result.completed_at = timezone.now()
            self.import_result.summary = summary
            self.import_result.notes = notes
            self.import_result.save()
    
    def fail_import(self, error_message):
        """Mark the import as failed"""
        if self.import_result:
            self.import_result.status = 'failed'
            self.import_result.completed_at = timezone.now()
            self.import_result.summary = f"Import failed: {error_message}"
            self.import_result.save()
    
    def process_import_export_result(self, result, dataset):
        """Process django-import-export result and update tracking"""
        if not self.import_result:
            return
        
        total_rows = len(dataset)
        successful_rows = 0
        failed_rows = 0
        
        # Process errors
        if hasattr(result, 'invalid_rows') and result.invalid_rows:
            for row_errors in result.invalid_rows:
                row_number = row_errors[0] + 1  # Convert to 1-based indexing
                errors = row_errors[1]
                row_data = dict(zip(dataset.headers, dataset[row_errors[0]]))
                
                for error in errors:
                    field_name = getattr(error, 'field', '')
                    error_message = str(error.error)
                    self.add_error(
                        row_number=row_number,
                        error_type='validation',
                        field_name=field_name,
                        error_message=error_message,
                        row_data=row_data
                    )
                failed_rows += 1
        
        # Process successful rows
        successful_rows = total_rows - failed_rows
        
        # If we have created instances, track them
        if hasattr(result, 'rows') and result.rows:
            for i, row_result in enumerate(result.rows):
                if row_result.import_type in ['new', 'update']:
                    row_data = dict(zip(dataset.headers, dataset[i]))
                    if row_result.object_id:
                        self.add_success(
                            row_number=i + 1,
                            created_object=row_result.object_repr or f"Object {row_result.object_id}",
                            row_data=row_data
                        )
        
        # Update totals
        self.update_totals(
            total_rows=total_rows,
            successful_rows=successful_rows,
            failed_rows=failed_rows
        )
        
        # Determine final status
        if failed_rows == 0:
            status = 'completed'
            summary = f"Successfully imported {successful_rows} out of {total_rows} rows."
        elif successful_rows == 0:
            status = 'failed'
            summary = f"Import failed. {failed_rows} out of {total_rows} rows had errors."
        else:
            status = 'partial'
            summary = f"Partial success. {successful_rows} rows imported, {failed_rows} rows failed out of {total_rows} total rows."
        
        self.complete_import(status=status, summary=summary)
        
        return self.import_result