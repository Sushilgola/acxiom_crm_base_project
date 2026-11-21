import re
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Customer, Lead, Opportunity, FollowUp, Activity
from core.models import User


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'company_name', 'address', 'city', 'state', 'status', 'assigned_to', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. John Doe', 'required': True, 'maxlength': '150'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'john@example.com', 'required': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210', 'required': True, 'pattern': r'^[0-9\+\-\s]{10,15}$'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company / Business'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Street Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State / Province'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional customer notes...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Sales reps can only assign to themselves if not admin/manager
        if user and not (user.is_admin_role or user.is_manager_role):
            self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
            self.fields['assigned_to'].initial = user
        else:
            self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        clean_num = re.sub(r'[\s\-\(\)\+]', '', phone)
        if not clean_num.isdigit() or len(clean_num) < 10 or len(clean_num) > 15:
            raise ValidationError("Enter a valid phone number (10 to 15 digits).")
        qs = Customer.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A customer with this phone number already exists.")
        return phone

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("Enter a valid email address.")
        qs = Customer.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A customer with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name', '').strip()
        company = cleaned_data.get('company_name', '').strip()

        if not name:
            self.add_error('name', "Customer Name is required.")

        # Duplicate checking by Name + Company
        if name and company:
            qs = Customer.objects.filter(name__iexact=name, company_name__iexact=company)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('name', f"A customer '{name}' at '{company}' already exists.")

        return cleaned_data


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name', 'email', 'phone', 'company_name', 'source', 'status', 'priority', 'expected_value', 'assigned_to', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Alice Smith', 'required': True, 'maxlength': '150'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'alice@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'expected_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Lead notes...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not (user.is_admin_role or user.is_manager_role):
            self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
            self.fields['assigned_to'].initial = user
        else:
            self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Lead name is mandatory.")
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            clean_num = re.sub(r'[\s\-\(\)\+]', '', phone)
            if not clean_num.isdigit() or len(clean_num) < 10 or len(clean_num) > 15:
                raise ValidationError("Enter a valid phone number (10 to 15 digits).")
        return phone

    def clean_expected_value(self):
        val = self.cleaned_data.get('expected_value')
        if val is not None and val < 0:
            raise ValidationError("Expected value cannot be negative.")
        return val or Decimal('0.00')

    def clean_status(self):
        status = self.cleaned_data.get('status')
        valid_statuses = [c[0] for c in Lead.STATUS_CHOICES]
        if status not in valid_statuses:
            raise ValidationError(f"Invalid lead status '{status}'.")
        if self.instance.pk:
            prev = Lead.objects.get(pk=self.instance.pk)
            if prev.status == 'Converted' and status != 'Converted':
                raise ValidationError("A converted lead cannot be moved back to an earlier status.")
        return status


class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ['name', 'customer', 'amount', 'stage', 'probability', 'expected_close_date', 'assigned_to', 'source', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Enterprise Cloud Migration', 'required': True}),
            'customer': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': 'Deal Amount', 'required': True}),
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'probability': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'placeholder': '0 - 100', 'required': True}),
            'expected_close_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Inbound / Outbound'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not (user.is_admin_role or user.is_manager_role):
            self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
            self.fields['customer'].queryset = Customer.objects.filter(assigned_to=user)
            self.fields['assigned_to'].initial = user
        else:
            self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
            self.fields['customer'].queryset = Customer.objects.all()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= 0:
            raise ValidationError("Opportunity Amount must be greater than 0.")
        return amount

    def clean_probability(self):
        prob = self.cleaned_data.get('probability')
        if prob is None or prob < 0 or prob > 100:
            raise ValidationError("Probability must be between 0 and 100.")
        return prob

    def clean_expected_close_date(self):
        close_date = self.cleaned_data.get('expected_close_date')
        stage = self.cleaned_data.get('stage')
        if stage not in ['Won', 'Lost'] and close_date:
            if close_date < timezone.localdate():
                raise ValidationError("Expected Close Date cannot be in the past.")
        return close_date


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['follow_up_type', 'subject', 'follow_up_date', 'follow_up_time', 'customer', 'lead', 'status', 'assigned_to', 'remarks']
        widgets = {
            'follow_up_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Discuss revised quote', 'required': True}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'follow_up_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'lead': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Follow-up agenda or notes...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not (user.is_admin_role or user.is_manager_role):
            self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
            self.fields['customer'].queryset = Customer.objects.filter(assigned_to=user)
            self.fields['lead'].queryset = Lead.objects.filter(assigned_to=user)
            self.fields['assigned_to'].initial = user
        else:
            self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        cust = cleaned_data.get('customer')
        lead = cleaned_data.get('lead')
        follow_date = cleaned_data.get('follow_up_date')
        status = cleaned_data.get('status')

        if not cust and not lead:
            raise ValidationError("Follow-up must be associated with either a Customer or a Lead.")

        # Business rule: follow_up_date cannot be earlier than today for planned follow-up
        if status == 'Planned' and follow_date:
            if follow_date < timezone.localdate():
                self.add_error('follow_up_date', "Follow-up date cannot be earlier than today.")

        return cleaned_data


class FollowUpRescheduleForm(forms.Form):
    new_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
        label="New Follow-up Date"
    )
    new_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="New Time"
    )
    reschedule_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Reason for rescheduling...', 'required': True}),
        label="Reason for Rescheduling"
    )

    def clean_new_date(self):
        new_date = self.cleaned_data.get('new_date')
        if new_date and new_date < timezone.localdate():
            raise ValidationError("Follow-up date cannot be earlier than today.")
        return new_date


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['activity_type', 'subject', 'activity_date', 'customer', 'lead', 'status', 'assigned_to', 'description']
        widgets = {
            'activity_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Discovery Call', 'required': True}),
            'activity_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'lead': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Meeting minutes, call outcomes, action items...'}),
        }


class LeadConversionForm(forms.Form):
    customer_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True}),
        label="Customer Name"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
        label="Customer Email"
    )
    phone = forms.CharField(
        max_length=25,
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True}),
        label="Customer Phone"
    )
    company_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Company Name"
    )
    create_opportunity = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'create_opp_checkbox'}),
        label="Create Sales Opportunity"
    )
    opportunity_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Annual License'}),
        label="Opportunity Name"
    )
    opportunity_amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        label="Opportunity Amount"
    )
    expected_close_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Expected Close Date"
    )

    def clean(self):
        cleaned_data = super().clean()
        create_opp = cleaned_data.get('create_opportunity')
        if create_opp:
            opp_name = cleaned_data.get('opportunity_name')
            opp_amt = cleaned_data.get('opportunity_amount')
            close_date = cleaned_data.get('expected_close_date')

            if not opp_name:
                self.add_error('opportunity_name', "Opportunity name is required when creating an opportunity.")
            if opp_amt is None or opp_amt <= 0:
                self.add_error('opportunity_amount', "Opportunity Amount must be greater than 0.")
            if not close_date:
                self.add_error('expected_close_date', "Expected close date is required.")
            elif close_date < timezone.localdate():
                self.add_error('expected_close_date', "Expected Close Date cannot be in the past.")

        return cleaned_data
