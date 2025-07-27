import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from services.models import Claim, ServiceRequest, AdjudicationResult

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Claim)
def auto_adjudicate_claim(sender, instance, created, **kwargs):
    """Automatically adjudicate claims when created"""
    if created and instance.status == 'N':
        try:
            # from services.functions.adjudication import process_claim_adjudication

            # Process adjudication
            result = process_claim_adjudication(instance)

            logger.info(f"Auto-adjudicated claim {instance.transaction_number}: {result.get_result_display()}")

            # Send notification based on result
            if result.result == 'APPROVED':
                send_claim_approval_notification(instance)
            elif result.result == 'DECLINED':
                send_claim_decline_notification(instance, result.decline_reason)
            elif result.result in ['PENDING_REVIEW', 'PENDING_CLINICAL']:
                send_claim_review_notification(instance)

        except Exception as e:
            logger.error(f"Failed to auto-adjudicate claim {instance.transaction_number}: {str(e)}")


@receiver(post_save, sender=ServiceRequest)
def auto_adjudicate_service_request(sender, instance, created, **kwargs):
    """Automatically adjudicate service requests when created"""
    if created and instance.status == 'P':
        try:
            from services.functions.adjudication import process_service_request_adjudication

            # Process adjudication
            result = process_service_request_adjudication(instance)

            logger.info(f"Auto-adjudicated service request {instance.request_number}: {result.get_result_display()}")

            # Reserve funds if approved
            if result.result == 'APPROVED':
                reserve_funds_for_authorization(instance, result.adjudicated_amount)
                send_authorization_notification(instance)
            elif result.result == 'DECLINED':
                send_service_request_decline_notification(instance, result.decline_reason)

        except Exception as e:
            logger.error(f"Failed to auto-adjudicate service request {instance.request_number}: {str(e)}")


@receiver(post_save, sender=AdjudicationResult)
def handle_adjudication_result(sender, instance, created, **kwargs):
    """Handle adjudication results and trigger appropriate actions"""
    if not created:  # Only process updates, not creation
        try:
            if instance.result == 'APPROVED' and instance.processing_type == 'MANUAL':
                # Manual approval - send notifications
                if instance.claim:
                    send_manual_claim_approval(instance.claim, instance.processed_by)
                elif instance.service_request:
                    send_manual_authorization_approval(instance.service_request, instance.processed_by)

            elif instance.result == 'DECLINED':
                # Declined - send decline notifications
                if instance.claim:
                    send_manual_claim_decline(instance.claim, instance.decline_reason)
                elif instance.service_request:
                    send_manual_authorization_decline(instance.service_request, instance.decline_reason)

        except Exception as e:
            logger.error(f"Failed to handle adjudication result: {str(e)}")
