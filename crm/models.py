import re
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_phone(value):
    if not value:
        return
    # Strip spaces, hyphens, plus
    clean_num = re.sub(r'[\s\-\(\)\+]', '', value)
    if not clean_num.isdigit() or len(clean_num) < 10 or len(clean_num) > 15:
        raise ValidationError('Enter a valid phone number (10 to 15 digits).')


class Customer(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Lead', 'Lead'),
        ('Former', 'Former'),
    ]

    customer_code = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    name = models.CharField(max_length=150, verbose_name="Customer Name")
    email = models.EmailField(unique=True, verbose_name="Email Address")
    phone = models.CharField(max_length=25, unique=True, validators=[validate_phone], verbose_name="Phone Number")
    company_name = models.CharField(max_length=150, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_customers'
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.customer_code})"

    def clean(self):
        super().clean()
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'Customer Name is required.'})
        if len(self.name.strip()) > 150:
            raise ValidationError({'name': 'Customer Name cannot exceed 150 characters.'})
        if not self.email or not self.email.strip():
            raise ValidationError({'email': 'Email is required.'})
        if not self.phone or not self.phone.strip():
            raise ValidationError({'phone': 'Phone number is required.'})

        # Check duplicate customer with identical name and company (excluding self)
        qs = Customer.objects.filter(
            name__iexact=self.name.strip(),
            company_name__iexact=self.company_name.strip()
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if self.company_name.strip() and qs.exists():
            raise ValidationError({'name': f"A customer '{self.name}' at company '{self.company_name}' already exists."})

    def save(self, *args, **kwargs):
        self.clean()
        if not self.customer_code:
            # Auto-generate code
            last_cust = Customer.objects.order_by('-id').first()
            next_id = (last_cust.id + 1) if last_cust else 1
            self.customer_code = f"CUST-{next_id:04d}"
        super().save(*args, **kwargs)


class Lead(models.Model):
    SOURCE_CHOICES = [
        ('Website', 'Website'),
        ('Referral', 'Referral'),
        ('Cold Call', 'Cold Call'),
        ('Advertisement', 'Advertisement'),
        ('Partner', 'Partner'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Qualified', 'Qualified'),
        ('Unqualified', 'Unqualified'),
        ('Converted', 'Converted'),
        ('Lost', 'Lost'),
    ]

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    lead_code = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    name = models.CharField(max_length=150, verbose_name="Lead Name")
    email = models.EmailField(blank=True, default='', verbose_name="Email Address")
    phone = models.CharField(max_length=25, blank=True, default='', validators=[validate_phone], verbose_name="Phone Number")
    company_name = models.CharField(max_length=150, blank=True, default='')
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='Website')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='New')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    expected_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Expected Value")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads'
    )
    converted_customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='converted_leads'
    )
    converted_opportunity = models.ForeignKey(
        'Opportunity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='originating_lead'
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.lead_code})"

    def clean(self):
        super().clean()
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'Lead name is mandatory.'})
        if self.expected_value is not None and self.expected_value < 0:
            raise ValidationError({'expected_value': 'Expected value cannot be negative.'})
        
        # Validate status transitions
        if self.pk:
            prev = Lead.objects.get(pk=self.pk)
            if prev.status == 'Converted' and self.status != 'Converted':
                raise ValidationError({'status': 'A converted lead cannot be reverted to another status.'})

    def save(self, *args, **kwargs):
        self.clean()
        if not self.lead_code:
            last_lead = Lead.objects.order_by('-id').first()
            next_id = (last_lead.id + 1) if last_lead else 1
            self.lead_code = f"LEAD-{next_id:04d}"
        super().save(*args, **kwargs)


class Opportunity(models.Model):
    STAGE_CHOICES = [
        ('Qualification', 'Qualification'),
        ('Proposal', 'Proposal'),
        ('Negotiation', 'Negotiation'),
        ('Won', 'Won'),
        ('Lost', 'Lost'),
    ]

    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Won', 'Won'),
        ('Lost', 'Lost'),
    ]

    opportunity_code = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    name = models.CharField(max_length=150, verbose_name="Opportunity Name")
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='opportunities'
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='opportunities'
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Deal Amount")
    stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default='Qualification')
    probability = models.IntegerField(default=50, verbose_name="Probability (%)")
    expected_close_date = models.DateField(verbose_name="Expected Close Date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_opportunities'
    )
    source = models.CharField(max_length=100, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - ${self.amount} ({self.stage})"

    @property
    def weighted_amount(self):
        if self.amount and self.probability is not None:
            return round((self.amount * Decimal(self.probability)) / Decimal('100.00'), 2)
        return Decimal('0.00')

    def clean(self):
        super().clean()
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'Opportunity Name is required.'})

        # Amount validation
        if self.amount is None or self.amount <= 0:
            raise ValidationError({'amount': 'Opportunity Amount must be greater than 0.'})

        # Probability validation
        if self.probability is None or self.probability < 0 or self.probability > 100:
            raise ValidationError({'probability': 'Probability must be between 0 and 100.'})

        # Expected Close Date validation for active/open opportunities
        if self.stage not in ['Won', 'Lost'] and self.status == 'Open':
            if self.expected_close_date and self.expected_close_date < timezone.localdate():
                raise ValidationError({'expected_close_date': 'Expected Close Date cannot be in the past.'})

    def save(self, *args, **kwargs):
        # Synchronize stage with status
        if self.stage == 'Won':
            self.status = 'Won'
            self.probability = 100
        elif self.stage == 'Lost':
            self.status = 'Lost'
            self.probability = 0
        else:
            self.status = 'Open'

        self.clean()
        if not self.opportunity_code:
            last_opp = Opportunity.objects.order_by('-id').first()
            next_id = (last_opp.id + 1) if last_opp else 1
            self.opportunity_code = f"OPP-{next_id:04d}"
        super().save(*args, **kwargs)


class FollowUp(models.Model):
    TYPE_CHOICES = [
        ('Call', 'Call'),
        ('Meeting', 'Meeting'),
        ('Email', 'Email'),
        ('Demo', 'Demo'),
        ('Task', 'Task'),
    ]

    STATUS_CHOICES = [
        ('Planned', 'Planned'),
        ('Completed', 'Completed'),
        ('Missed', 'Missed'),
        ('Cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='followups'
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='followups'
    )
    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='followups'
    )
    follow_up_date = models.DateField(verbose_name="Follow-up Date")
    follow_up_time = models.TimeField(null=True, blank=True, verbose_name="Time")
    follow_up_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='Call')
    subject = models.CharField(max_length=200, verbose_name="Subject")
    remarks = models.TextField(blank=True, default='', verbose_name="Remarks/Notes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Planned')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_followups'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['follow_up_date', 'follow_up_time']

    def __str__(self):
        return f"{self.follow_up_type}: {self.subject} ({self.status})"

    @property
    def is_overdue(self):
        return self.status == 'Planned' and self.follow_up_date < timezone.localdate()

    @property
    def is_today(self):
        return self.status == 'Planned' and self.follow_up_date == timezone.localdate()

    def clean(self):
        super().clean()
        if not self.subject or not self.subject.strip():
            raise ValidationError({'subject': 'Subject is required.'})

        if not self.customer and not self.lead:
            raise ValidationError('Follow-up must be associated with either a Customer or a Lead.')

        # Date validation for new/planned follow-up
        if self.status == 'Planned':
            if self.follow_up_date and self.follow_up_date < timezone.localdate():
                raise ValidationError({'follow_up_date': 'Follow-up date cannot be earlier than today.'})


class Activity(models.Model):
    TYPE_CHOICES = [
        ('Call', 'Call'),
        ('Meeting', 'Meeting'),
        ('Email', 'Email'),
        ('Task', 'Task'),
        ('Note', 'Note'),
    ]

    STATUS_CHOICES = [
        ('Planned', 'Planned'),
        ('In-Progress', 'In-Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    activity_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='Call')
    subject = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    activity_date = models.DateTimeField(default=timezone.now)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Completed')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-activity_date']

    def __str__(self):
        return f"[{self.activity_type}] {self.subject}"
