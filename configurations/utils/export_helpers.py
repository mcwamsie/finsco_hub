class FormattedExporter:
    """Helper class for formatted exports"""

    @staticmethod
    def export_member_summary(queryset):
        """Export member summary with calculated fields"""

        data = []
        for member in queryset:
            data.append({
                'Membership Number': member.membership_number,
                'Name': member.name,
                'Type': member.get_type_display(),
                'Status': member.get_status_display(),
                'Beneficiaries Count': member.beneficiaries.count(),
                'Current Balance': getattr(member.accounts.first(), 'available_balance', 0),
                'Date Joined': member.date_joined.strftime('%Y-%m-%d'),
                'Registered By': member.registered_by.name if member.registered_by else '',
            })

        return data

    @staticmethod
    def export_claims_summary(queryset):
        """Export claims with summary information"""

        data = []
        for claim in queryset:
            data.append({
                'Transaction Number': claim.transaction_number,
                'Beneficiary': f"{claim.beneficiary.first_name} {claim.beneficiary.last_name}",
                'Membership Number': claim.beneficiary.membership_number,
                'Provider': claim.provider.name,
                'Claimed Amount': float(claim.claimed_amount),
                'Accepted Amount': float(claim.accepted_amount),
                'Status': claim.get_status_display(),
                'Date Submitted': claim.created_at.strftime('%Y-%m-%d'),
                'Service Date': claim.start_date.strftime('%Y-%m-%d'),
            })

        return data