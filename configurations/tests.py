from django.test import TestCase
from django.core.exceptions import ValidationError
from configurations.models import Member, Currency, Package


class MemberHierarchyValidationTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create required related objects
        self.currency = Currency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$'
        )
        
        self.package = Package.objects.create(
            name='Test Package',
            description='Test package for validation',
            global_annual_limit=50000.00,
            monthly_contribution=100.00
        )
        
        # Create a valid parent member (Community)
        self.parent_member = Member.objects.create(
            name='Test Community',
            type='CM',
            currency=self.currency,
            address_line_1='123 Test St',
            mobile='+1234567890',
            email='community@test.com',
            signing_rule='S',
            status='A',
            sponsor='S',
            default_package=self.package
        )

    def test_individual_member_requires_parent(self):
        """Test that Individual members must have a parent"""
        with self.assertRaises(ValidationError) as context:
            member = Member(
                name='Test Individual',
                type='IN',
                currency=self.currency,
                address_line_1='123 Test St',
                mobile='+1234567890',
                email='individual@test.com',
                signing_rule='S',
                status='A',
                sponsor='S',
                default_package=self.package
            )
            member.clean()
        
        self.assertIn('parent', context.exception.message_dict)
        self.assertIn('must have a parent', str(context.exception.message_dict['parent'][0]))

    def test_healthsave_member_requires_parent(self):
        """Test that HealthSave members must have a parent"""
        with self.assertRaises(ValidationError) as context:
            member = Member(
                name='Test HealthSave',
                type='HS',
                currency=self.currency,
                address_line_1='123 Test St',
                mobile='+1234567890',
                email='healthsave@test.com',
                signing_rule='S',
                status='A',
                sponsor='S',
                default_package=self.package
            )
            member.clean()
        
        self.assertIn('parent', context.exception.message_dict)

    def test_individual_member_with_valid_parent_succeeds(self):
        """Test that Individual members with valid parents pass validation"""
        member = Member(
            name='Test Individual',
            type='IN',
            currency=self.currency,
            address_line_1='123 Test St',
            mobile='+1234567890',
            email='individual@test.com',
            signing_rule='S',
            status='A',
            sponsor='S',
            default_package=self.package,
            parent=self.parent_member
        )
        
        # Should not raise ValidationError
        try:
            member.clean()
        except ValidationError:
            self.fail("Individual member with valid parent should pass validation")

    def test_community_member_cannot_be_child(self):
        """Test that Community members cannot be children"""
        with self.assertRaises(ValidationError) as context:
            member = Member(
                name='Test Community Child',
                type='CM',
                currency=self.currency,
                address_line_1='123 Test St',
                mobile='+1234567890',
                email='community_child@test.com',
                signing_rule='S',
                status='A',
                sponsor='S',
                default_package=self.package,
                parent=self.parent_member
            )
            member.clean()
        
        self.assertIn('parent', context.exception.message_dict)
        self.assertIn('cannot be child members', str(context.exception.message_dict['parent'][0]))

    def test_corporate_member_can_be_standalone(self):
        """Test that Corporate members can be standalone"""
        member = Member(
            name='Test Corporate',
            type='CO',
            currency=self.currency,
            address_line_1='123 Test St',
            mobile='+1234567890',
            email='corporate@test.com',
            signing_rule='S',
            status='A',
            sponsor='S',
            default_package=self.package
        )
        
        # Should not raise ValidationError
        try:
            member.clean()
        except ValidationError:
            self.fail("Corporate member should be able to be standalone")

    def test_family_member_can_be_standalone(self):
        """Test that Family members can be standalone"""
        member = Member(
            name='Test Family',
            type='FM',
            currency=self.currency,
            address_line_1='123 Test St',
            mobile='+1234567890',
            email='family@test.com',
            signing_rule='S',
            status='A',
            sponsor='S',
            default_package=self.package
        )
        
        # Should not raise ValidationError
        try:
            member.clean()
        except ValidationError:
            self.fail("Family member should be able to be standalone")

    def test_manager_valid_parents_method(self):
        """Test the valid_parents manager method"""
        # Create different types of members
        corporate = Member.objects.create(
            name='Corporate Member',
            type='CO',
            currency=self.currency,
            address_line_1='123 Test St',
            mobile='+1234567890',
            email='corporate@test.com',
            signing_rule='S',
            status='A',
            sponsor='S',
            default_package=self.package
        )
        
        family = Member.objects.create(
            name='Family Member',
            type='FM',
            currency=self.currency,
            address_line_1='123 Test St',
            mobile='+1234567891',
            email='family@test.com',
            signing_rule='S',
            status='A',
            sponsor='S',
            default_package=self.package
        )
        
        # Test valid_parents method
        valid_parents = Member.objects.valid_parents()
        self.assertIn(self.parent_member, valid_parents)  # Community
        self.assertIn(corporate, valid_parents)  # Corporate
        self.assertIn(family, valid_parents)  # Family
        
        # Should only return 3 members (CM, CO, FM)
        self.assertEqual(valid_parents.count(), 3)
