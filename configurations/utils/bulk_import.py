import pandas as pd
from django.db import transaction
from django.core.exceptions import ValidationError


class BulkImporter:
    """Utility class for handling bulk imports with better error handling"""

    def __init__(self, resource_class, model_class):
        self.resource_class = resource_class
        self.model_class = model_class
        self.errors = []
        self.success_count = 0
        self.skip_count = 0

    def import_from_dataframe(self, df, dry_run=True, batch_size=100):
        """Import data from pandas DataFrame in batches"""

        total_rows = len(df)
        processed = 0

        with transaction.atomic():
            for start_idx in range(0, total_rows, batch_size):
                end_idx = min(start_idx + batch_size, total_rows)
                batch_df = df.iloc[start_idx:end_idx]

                batch_result = self._process_batch(batch_df, dry_run)
                processed += len(batch_df)

                # Log progress
                print(f"Processed {processed}/{total_rows} rows")

        return {
            'success_count': self.success_count,
            'skip_count': self.skip_count,
            'error_count': len(self.errors),
            'errors': self.errors
        }

    def _process_batch(self, batch_df, dry_run):
        """Process a batch of rows"""

        for idx, row in batch_df.iterrows():
            try:
                # Convert row to dict
                row_data = row.to_dict()

                # Create resource instance
                resource = self.resource_class()

                # Import the row
                result = resource.import_row(row_data, dry_run=dry_run)

                if result.errors:
                    self.errors.append({
                        'row': idx,
                        'data': row_data,
                        'errors': result.errors
                    })
                else:
                    self.success_count += 1

            except Exception as e:
                self.errors.append({
                    'row': idx,
                    'data': row.to_dict(),
                    'errors': [str(e)]
                })
