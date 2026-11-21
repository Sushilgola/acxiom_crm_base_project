import re
from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone
from core.models import User, Role
from crm.models import Customer, Lead, Opportunity, FollowUp, Activity


class UserDTO(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role_name', 'role_display', 'phone', 'is_active']
        read_only_fields = ['id', 'role_display']


class CustomerDTO(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_code', 'name', 'email', 'phone', 'company_name',
            'address', 'city', 'state', 'status', 'assigned_to', 'assigned_to_name',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_code', 'created_at', 'updated_at', 'assigned_to_name']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Customer Name is required.")
        return value.strip()

    def validate_phone(self, value):
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        clean_num = re.sub(r'[\s\-\(\)\+]', '', value)
        if not clean_num.isdigit() or len(clean_num) < 10 or len(clean_num) > 15:
            raise serializers.ValidationError("Enter a valid phone number (10 to 15 digits).")
        qs = Customer.objects.filter(phone=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A customer with this phone number already exists.")
        return value

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        qs = Customer.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A customer with this email address already exists.")
        return value.lower()


class LeadDTO(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'lead_code', 'name', 'email', 'phone', 'company_name',
            'source', 'status', 'priority', 'expected_value', 'assigned_to',
            'assigned_to_name', 'converted_customer', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'lead_code', 'converted_customer', 'created_at', 'updated_at', 'assigned_to_name']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Lead name is mandatory.")
        return value.strip()

    def validate_expected_value(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Expected value cannot be negative.")
        return value

    def validate_status(self, value):
        if self.instance and self.instance.status == 'Converted' and value != 'Converted':
            raise serializers.ValidationError("A converted lead cannot be reverted.")
        return value


class OpportunityDTO(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    weighted_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            'id', 'opportunity_code', 'name', 'customer', 'customer_name', 'lead',
            'amount', 'stage', 'probability', 'expected_close_date', 'status',
            'assigned_to', 'assigned_to_name', 'weighted_amount', 'source', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'opportunity_code', 'customer_name', 'assigned_to_name', 'weighted_amount', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Opportunity Amount must be greater than 0.")
        return value

    def validate_probability(self, value):
        if value is None or value < 0 or value > 100:
            raise serializers.ValidationError("Probability must be between 0 and 100.")
        return value

    def validate(self, attrs):
        stage = attrs.get('stage', getattr(self.instance, 'stage', 'Qualification'))
        close_date = attrs.get('expected_close_date', getattr(self.instance, 'expected_close_date', None))
        if stage not in ['Won', 'Lost'] and close_date:
            if close_date < timezone.localdate():
                raise serializers.ValidationError({'expected_close_date': "Expected Close Date cannot be in the past."})
        return attrs


class FollowUpDTO(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_today = serializers.BooleanField(read_only=True)

    class Meta:
        model = FollowUp
        fields = [
            'id', 'customer', 'customer_name', 'lead', 'lead_name',
            'follow_up_date', 'follow_up_time', 'follow_up_type',
            'subject', 'remarks', 'status', 'assigned_to', 'assigned_to_name',
            'is_overdue', 'is_today', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_name', 'lead_name', 'assigned_to_name', 'is_overdue', 'is_today', 'created_at', 'updated_at']

    def validate(self, attrs):
        cust = attrs.get('customer', getattr(self.instance, 'customer', None))
        lead = attrs.get('lead', getattr(self.instance, 'lead', None))
        follow_date = attrs.get('follow_up_date', getattr(self.instance, 'follow_up_date', None))
        status = attrs.get('status', getattr(self.instance, 'status', 'Planned'))

        if not cust and not lead:
            raise serializers.ValidationError("Follow-up must be associated with either a Customer or a Lead.")

        if status == 'Planned' and follow_date:
            if follow_date < timezone.localdate():
                raise serializers.ValidationError({'follow_up_date': "Follow-up date cannot be earlier than today."})

        return attrs
