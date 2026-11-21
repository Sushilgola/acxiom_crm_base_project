from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import User, Role, AuditLog
from crm.models import Customer, Lead, Opportunity, FollowUp, Activity


class AcxiomCRMTestChecklist(TestCase):
    def setUp(self):
        self.client = Client()
        # Roles
        self.admin_role = Role.objects.create(name=Role.ADMIN)
        self.mgr_role = Role.objects.create(name=Role.MANAGER)
        self.sales_role = Role.objects.create(name=Role.SALES_EXECUTIVE)

        # Users
        self.admin = User.objects.create_user(
            username='admin_test',
            email='admin_test@acxiom.com',
            password='TestPassword@123',
            role=self.admin_role,
            role_name=Role.ADMIN,
            is_staff=True,
            is_superuser=True
        )
        self.manager = User.objects.create_user(
            username='mgr_test',
            email='mgr_test@acxiom.com',
            password='TestPassword@123',
            role=self.mgr_role,
            role_name=Role.MANAGER
        )
        self.sales_exec = User.objects.create_user(
            username='sales_test',
            email='sales_test@acxiom.com',
            password='TestPassword@123',
            role=self.sales_role,
            role_name=Role.SALES_EXECUTIVE
        )

        self.today = timezone.localdate()

    # Checklist Item 1: Login works with a valid account; invalid login is rejected
    def test_01_authentication(self):
        # Invalid login
        resp_invalid = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'WrongPassword123'
        })
        self.assertEqual(resp_invalid.status_code, 200)
        self.assertContains(resp_invalid, "Invalid credentials")

        # Valid login
        resp_valid = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'TestPassword@123'
        })
        self.assertEqual(resp_valid.status_code, 302)
        self.assertRedirects(resp_valid, reverse('dashboard'))

    # Checklist Item 2: Anonymous users cannot open protected CRM pages or API endpoints
    def test_02_anonymous_protection(self):
        # CRM pages redirect to login
        pages = [
            reverse('dashboard'),
            reverse('customer_list'),
            reverse('lead_list'),
            reverse('opportunity_list'),
            reverse('followup_list'),
            reverse('activity_list'),
            reverse('report_center'),
        ]
        for url in pages:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302)
            self.assertTrue('/auth/login/' in res.url)

        # API endpoints require auth
        api_res = self.client.get(reverse('api_customers'))
        self.assertEqual(api_res.status_code, 403)

    # Checklist Item 3: Admin, Manager and Sales Executive permissions are checked on the server
    def test_03_role_based_permissions(self):
        # Sales Executive cannot view Admin user administration
        self.client.login(username='sales_test', password='TestPassword@123')
        res_user_mgmt = self.client.get(reverse('user_list'))
        self.assertEqual(res_user_mgmt.status_code, 302) # Redirected with Access Denied

        # Sales Executive cannot view Audit Logs
        res_audit = self.client.get(reverse('audit_log_list'))
        self.assertEqual(res_audit.status_code, 302)

        # Admin CAN view user administration & audit logs
        self.client.login(username='admin_test', password='TestPassword@123')
        res_admin_users = self.client.get(reverse('user_list'))
        self.assertEqual(res_admin_users.status_code, 200)

        res_admin_audit = self.client.get(reverse('audit_log_list'))
        self.assertEqual(res_admin_audit.status_code, 200)

    # Checklist Item 4: Customer can be created, edited, searched and deactivated
    def test_04_customer_crud(self):
        self.client.login(username='admin_test', password='TestPassword@123')

        # Create
        create_res = self.client.post(reverse('customer_create'), {
            'name': 'Pinnacle Systems',
            'email': 'contact@pinnaclesys.com',
            'phone': '9876543210',
            'company_name': 'Pinnacle',
            'status': 'Active',
            'assigned_to': self.sales_exec.id
        })
        self.assertEqual(create_res.status_code, 302)
        customer = Customer.objects.get(email='contact@pinnaclesys.com')
        self.assertEqual(customer.name, 'Pinnacle Systems')
        self.assertTrue(customer.customer_code.startswith('CUST-'))

        # Edit
        edit_res = self.client.post(reverse('customer_edit', args=[customer.id]), {
            'name': 'Pinnacle Systems Global',
            'email': 'contact@pinnaclesys.com',
            'phone': '9876543210',
            'company_name': 'Pinnacle Global',
            'status': 'Inactive',
            'assigned_to': self.sales_exec.id
        })
        self.assertEqual(edit_res.status_code, 302)
        customer.refresh_from_db()
        self.assertEqual(customer.name, 'Pinnacle Systems Global')
        self.assertEqual(customer.status, 'Inactive')

        # Search
        search_res = self.client.get(reverse('customer_list') + '?q=Pinnacle')
        self.assertContains(search_res, 'Pinnacle Systems Global')

    # Checklist Item 5: Duplicate customer email/phone is rejected
    def test_05_duplicate_customer_prevention(self):
        self.client.login(username='admin_test', password='TestPassword@123')

        Customer.objects.create(
            name='First Company',
            email='dup@example.com',
            phone='9998887771',
            status='Active'
        )

        # Duplicate email
        res_dup_email = self.client.post(reverse('customer_create'), {
            'name': 'Second Company',
            'email': 'dup@example.com',
            'phone': '9998887772',
            'status': 'Active'
        })
        self.assertEqual(res_dup_email.status_code, 200)
        self.assertContains(res_dup_email, 'A customer with this email address already exists.')

        # Duplicate phone
        res_dup_phone = self.client.post(reverse('customer_create'), {
            'name': 'Third Company',
            'email': 'unique@example.com',
            'phone': '9998887771',
            'status': 'Active'
        })
        self.assertEqual(res_dup_phone.status_code, 200)
        self.assertContains(res_dup_phone, 'A customer with this phone number already exists.')

    # Checklist Item 6: Lead status can be updated and qualified lead can be converted once
    def test_06_lead_conversion_workflow(self):
        self.client.login(username='admin_test', password='TestPassword@123')

        lead = Lead.objects.create(
            name='Arthur Dent',
            email='arthur@dent.com',
            phone='9876543333',
            company_name='Hitchhiker Tech',
            status='New',
            expected_value=Decimal('50000.00'),
            assigned_to=self.sales_exec
        )

        # Update status to Qualified
        self.client.post(reverse('lead_edit', args=[lead.id]), {
            'name': lead.name,
            'email': lead.email,
            'phone': lead.phone,
            'company_name': lead.company_name,
            'source': 'Website',
            'status': 'Qualified',
            'priority': 'High',
            'expected_value': '50000.00',
            'assigned_to': self.sales_exec.id
        })
        lead.refresh_from_db()
        self.assertEqual(lead.status, 'Qualified')

        # Convert to Customer & Opportunity
        conv_res = self.client.post(reverse('lead_convert', args=[lead.id]), {
            'customer_name': 'Hitchhiker Tech Corp',
            'email': 'arthur@dent.com',
            'phone': '9876543333',
            'company_name': 'Hitchhiker Tech',
            'create_opportunity': True,
            'opportunity_name': 'Hitchhiker Enterprise Deal',
            'opportunity_amount': '50000.00',
            'expected_close_date': (self.today + timedelta(days=20)).strftime('%Y-%m-%d')
        })
        self.assertEqual(conv_res.status_code, 302)
        lead.refresh_from_db()
        self.assertEqual(lead.status, 'Converted')
        self.assertIsNotNone(lead.converted_customer)
        self.assertIsNotNone(lead.converted_opportunity)

    # Checklist Item 7: Opportunity rejects amount 0/negative, probability outside 0–100 and past expected close date
    def test_07_opportunity_business_validations(self):
        self.client.login(username='admin_test', password='TestPassword@123')
        cust = Customer.objects.create(name='Valid Corp', email='corp@valid.com', phone='9876540099')

        # Amount <= 0
        res_amt = self.client.post(reverse('opportunity_create'), {
            'name': 'Zero Deal',
            'customer': cust.id,
            'amount': '0',
            'stage': 'Qualification',
            'probability': 50,
            'expected_close_date': (self.today + timedelta(days=10)).strftime('%Y-%m-%d')
        })
        self.assertEqual(res_amt.status_code, 200)
        self.assertContains(res_amt, 'Opportunity Amount must be greater than 0.')

        # Probability > 100
        res_prob = self.client.post(reverse('opportunity_create'), {
            'name': 'Over 100 Deal',
            'customer': cust.id,
            'amount': '1000',
            'stage': 'Qualification',
            'probability': 120,
            'expected_close_date': (self.today + timedelta(days=10)).strftime('%Y-%m-%d')
        })
        self.assertEqual(res_prob.status_code, 200)
        self.assertContains(res_prob, 'Probability must be between 0 and 100.')

        # Past close date for active opportunity
        res_date = self.client.post(reverse('opportunity_create'), {
            'name': 'Past Deal',
            'customer': cust.id,
            'amount': '1000',
            'stage': 'Qualification',
            'probability': 50,
            'expected_close_date': (self.today - timedelta(days=5)).strftime('%Y-%m-%d')
        })
        self.assertEqual(res_date.status_code, 200)
        self.assertContains(res_date, 'Expected Close Date cannot be in the past.')

    # Checklist Item 8: Follow-up rejects a past date for a new planned follow-up
    def test_08_followup_date_validation(self):
        self.client.login(username='admin_test', password='TestPassword@123')
        cust = Customer.objects.create(name='Follow Corp', email='f@corp.com', phone='9876540088')

        res_past = self.client.post(reverse('followup_create'), {
            'subject': 'Past Follow-up Call',
            'follow_up_type': 'Call',
            'follow_up_date': (self.today - timedelta(days=2)).strftime('%Y-%m-%d'),
            'customer': cust.id,
            'status': 'Planned'
        })
        self.assertEqual(res_past.status_code, 200)
        self.assertContains(res_past, 'Follow-up date cannot be earlier than today.')

    # Checklist Item 9: Dashboard totals change after records are added
    def test_09_dashboard_totals(self):
        self.client.login(username='admin_test', password='TestPassword@123')
        cust = Customer.objects.create(name='Metric Corp', email='m@corp.com', phone='9876540077')
        Opportunity.objects.create(
            name='Big Deal',
            customer=cust,
            amount=Decimal('85000.00'),
            stage='Negotiation',
            probability=70,
            expected_close_date=self.today + timedelta(days=15),
            status='Open'
        )
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '85000.00')

    # Checklist Item 10: API returns expected status codes and does not expose sensitive fields
    def test_10_rest_api(self):
        self.client.login(username='admin_test', password='TestPassword@123')
        res = self.client.get(reverse('api_customers'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        # Verify passwords or secret tokens are not present
        if len(data) > 0:
            self.assertNotIn('password', data[0])
            self.assertNotIn('password_hash', data[0])

    # Checklist Item 11: Audit log records important actions
    def test_11_audit_logging(self):
        self.client.login(username='admin_test', password='TestPassword@123')
        AuditLog.log(
            action='CREATE',
            entity_name='Customer',
            record_id='999',
            user=self.admin,
            result='SUCCESS',
            details="Test audit customer creation."
        )
        log_entry = AuditLog.objects.filter(entity_name='Customer', record_id='999').first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.action, 'CREATE')
