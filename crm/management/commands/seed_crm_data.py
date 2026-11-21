from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import User, Role, AuditLog
from crm.models import Customer, Lead, Opportunity, FollowUp, Activity


class Command(BaseCommand):
    help = 'Seeds AcxiomCRM roles, demo accounts (Admin, Manager, SalesExecutive), and realistic CRM data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing AcxiomCRM database seed..."))

        # 1. Create Roles
        admin_role, _ = Role.objects.get_or_create(
            name=Role.ADMIN,
            defaults={'description': 'Full application administration, all CRM records, audit logs, and configuration.'}
        )
        mgr_role, _ = Role.objects.get_or_create(
            name=Role.MANAGER,
            defaults={'description': 'Team pipeline oversight, sales analytics, management reports, no unrestricted security admin.'}
        )
        sales_role, _ = Role.objects.get_or_create(
            name=Role.SALES_EXECUTIVE,
            defaults={'description': 'Assigned customers, leads, deals, follow-ups, and personal sales reports.'}
        )
        self.stdout.write(self.style.SUCCESS("✓ Roles initialized (Admin, Manager, SalesExecutive)"))

        # 2. Create Users
        # Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@acxiom.com',
                'first_name': 'Alexander',
                'last_name': 'Pierce',
                'role': admin_role,
                'role_name': Role.ADMIN,
                'phone': '9876540001',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created or not admin_user.check_password('Admin@12345'):
            admin_user.set_password('Admin@12345')
            admin_user.role = admin_role
            admin_user.role_name = Role.ADMIN
            admin_user.save()

        # Manager User
        mgr_user, created = User.objects.get_or_create(
            username='manager',
            defaults={
                'email': 'manager@acxiom.com',
                'first_name': 'Eleanor',
                'last_name': 'Vance',
                'role': mgr_role,
                'role_name': Role.MANAGER,
                'phone': '9876540002',
                'is_staff': False,
                'is_active': True,
            }
        )
        if created or not mgr_user.check_password('Manager@12345'):
            mgr_user.set_password('Manager@12345')
            mgr_user.role = mgr_role
            mgr_user.role_name = Role.MANAGER
            mgr_user.save()

        # Sales Exec 1
        sales1, created = User.objects.get_or_create(
            username='sales1',
            defaults={
                'email': 'sales1@acxiom.com',
                'first_name': 'Marcus',
                'last_name': 'Reed',
                'role': sales_role,
                'role_name': Role.SALES_EXECUTIVE,
                'phone': '9876540003',
                'is_staff': False,
                'is_active': True,
            }
        )
        if created or not sales1.check_password('Sales@12345'):
            sales1.set_password('Sales@12345')
            sales1.role = sales_role
            sales1.role_name = Role.SALES_EXECUTIVE
            sales1.save()

        # Sales Exec 2
        sales2, created = User.objects.get_or_create(
            username='sales2',
            defaults={
                'email': 'sales2@acxiom.com',
                'first_name': 'Sophia',
                'last_name': 'Chen',
                'role': sales_role,
                'role_name': Role.SALES_EXECUTIVE,
                'phone': '9876540004',
                'is_staff': False,
                'is_active': True,
            }
        )
        if created or not sales2.check_password('Sales@12345'):
            sales2.set_password('Sales@12345')
            sales2.role = sales_role
            sales2.role_name = Role.SALES_EXECUTIVE
            sales2.save()

        self.stdout.write(self.style.SUCCESS("✓ Demo users created (admin@acxiom.com, manager@acxiom.com, sales1@acxiom.com, sales2@acxiom.com)"))

        # 3. Create Sample Customers
        c1, _ = Customer.objects.get_or_create(
            email='it@apexfinancial.com',
            defaults={
                'name': 'Apex Financial Technologies',
                'phone': '9876541001',
                'company_name': 'Apex Financial Tech',
                'address': '742 Evergreen Terrace, Suite 500',
                'city': 'New York',
                'state': 'NY',
                'status': 'Active',
                'assigned_to': sales1,
                'notes': 'Key accounts tier 1 client looking for core banking CRM integration.'
            }
        )

        c2, _ = Customer.objects.get_or_create(
            email='procurement@horizonhealth.org',
            defaults={
                'name': 'Horizon Health Network',
                'phone': '9876541002',
                'company_name': 'Horizon Healthcare',
                'address': '1200 Medical Center Blvd',
                'city': 'Chicago',
                'state': 'IL',
                'status': 'Active',
                'assigned_to': sales1,
                'notes': 'Healthcare provider network managing 14 clinics.'
            }
        )

        c3, _ = Customer.objects.get_or_create(
            email='ops@stratuslogistics.com',
            defaults={
                'name': 'Stratus Logistics Global',
                'phone': '9876541003',
                'company_name': 'Stratus Logistics',
                'address': '88 Oceanview Highway',
                'city': 'Seattle',
                'state': 'WA',
                'status': 'Active',
                'assigned_to': sales2,
                'notes': 'Freight and supply chain partner.'
            }
        )

        c4, _ = Customer.objects.get_or_create(
            email='contact@solarisretail.com',
            defaults={
                'name': 'Solaris Retail Group',
                'phone': '9876541004',
                'company_name': 'Solaris Retail',
                'address': '450 Marketplace Ave',
                'city': 'Austin',
                'state': 'TX',
                'status': 'Inactive',
                'assigned_to': sales2,
                'notes': 'Omnichannel retail chain.'
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ Sample Customers created."))

        # 4. Create Sample Leads
        l1, _ = Lead.objects.get_or_create(
            email='david@quantumdynamics.io',
            defaults={
                'name': 'David Miller',
                'phone': '9876542001',
                'company_name': 'Quantum Dynamics',
                'source': 'Website',
                'status': 'Qualified',
                'priority': 'High',
                'expected_value': Decimal('45000.00'),
                'assigned_to': sales1,
                'notes': 'Inquired about enterprise cloud deployment.'
            }
        )

        l2, _ = Lead.objects.get_or_create(
            email='sarah@vanguardmedia.com',
            defaults={
                'name': 'Sarah Connor',
                'phone': '9876542002',
                'company_name': 'Vanguard Media Group',
                'source': 'Referral',
                'status': 'Contacted',
                'priority': 'Medium',
                'expected_value': Decimal('18000.00'),
                'assigned_to': sales1,
                'notes': 'Initial discovery call conducted. Requested proposal.'
            }
        )

        l3, _ = Lead.objects.get_or_create(
            email='kevin@nexusrobotics.ai',
            defaults={
                'name': 'Kevin Zhang',
                'phone': '9876542003',
                'company_name': 'Nexus Robotics',
                'source': 'Advertisement',
                'status': 'New',
                'priority': 'High',
                'expected_value': Decimal('60000.00'),
                'assigned_to': sales2,
                'notes': 'Inbound inquiry from tech summit demo.'
            }
        )

        l4, _ = Lead.objects.get_or_create(
            email='lisa@greenleafbio.com',
            defaults={
                'name': 'Lisa Cuddy',
                'phone': '9876542004',
                'company_name': 'Greenleaf Biotech',
                'source': 'Partner',
                'status': 'Converted',
                'priority': 'Medium',
                'expected_value': Decimal('25000.00'),
                'assigned_to': sales2,
                'converted_customer': c3,
                'notes': 'Lead converted into customer Stratus Logistics.'
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ Sample Leads created."))

        # 5. Create Sample Opportunities
        today = timezone.localdate()
        o1, _ = Opportunity.objects.get_or_create(
            name='Enterprise Cloud Modernization',
            customer=c1,
            defaults={
                'amount': Decimal('75000.00'),
                'stage': 'Proposal',
                'probability': 60,
                'expected_close_date': today + timedelta(days=25),
                'status': 'Open',
                'assigned_to': sales1,
                'source': 'Referral',
                'notes': 'Proposal delivered, awaiting steering committee review.'
            }
        )

        o2, _ = Opportunity.objects.get_or_create(
            name='Hospital Management Software Expansion',
            customer=c2,
            defaults={
                'amount': Decimal('120000.00'),
                'stage': 'Negotiation',
                'probability': 80,
                'expected_close_date': today + timedelta(days=15),
                'status': 'Open',
                'assigned_to': sales1,
                'source': 'Website',
                'notes': 'Final commercial terms and SLA in legal review.'
            }
        )

        o3, _ = Opportunity.objects.get_or_create(
            name='Global Freight Automation Platform',
            customer=c3,
            defaults={
                'amount': Decimal('95000.00'),
                'stage': 'Won',
                'probability': 100,
                'expected_close_date': today - timedelta(days=10),
                'status': 'Won',
                'assigned_to': sales2,
                'source': 'Partner',
                'notes': 'Contract signed and initial deposit received.'
            }
        )

        o4, _ = Opportunity.objects.get_or_create(
            name='Legacy POS Modernization',
            customer=c4,
            defaults={
                'amount': Decimal('35000.00'),
                'stage': 'Lost',
                'probability': 0,
                'expected_close_date': today - timedelta(days=30),
                'status': 'Lost',
                'assigned_to': sales2,
                'source': 'Cold Call',
                'notes': 'Client paused budget due to corporate restructuring.'
            }
        )

        o5, _ = Opportunity.objects.get_or_create(
            name='Analytics & Compliance Reporting Suite',
            customer=c1,
            defaults={
                'amount': Decimal('40000.00'),
                'stage': 'Qualification',
                'probability': 30,
                'expected_close_date': today + timedelta(days=45),
                'status': 'Open',
                'assigned_to': sales1,
                'source': 'Account Upsell',
                'notes': 'Add-on module demonstration scheduled.'
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ Sample Opportunities created."))

        # 6. Create Sample Follow-Ups (Today, Overdue, Upcoming, Completed)
        # Due Today
        FollowUp.objects.get_or_create(
            subject='Present revised financial terms to CFO',
            customer=c1,
            defaults={
                'follow_up_date': today,
                'follow_up_type': 'Meeting',
                'status': 'Planned',
                'assigned_to': sales1,
                'remarks': 'Review commercial proposal adjustments.'
            }
        )

        # Overdue
        FollowUp.objects.get_or_create(
            subject='Confirm technical security architecture call',
            customer=c2,
            defaults={
                'follow_up_date': today - timedelta(days=2),
                'follow_up_type': 'Call',
                'status': 'Planned',
                'assigned_to': sales1,
                'remarks': 'Coordinate with hospital IT security lead.'
            }
        )

        # Upcoming
        FollowUp.objects.get_or_create(
            subject='Product demonstration for Nexus Robotics engineering team',
            lead=l3,
            defaults={
                'follow_up_date': today + timedelta(days=4),
                'follow_up_type': 'Demo',
                'status': 'Planned',
                'assigned_to': sales2,
                'remarks': 'Present API capabilities and SDK integrations.'
            }
        )

        # Completed
        FollowUp.objects.get_or_create(
            subject='Initial onboarding check-in call',
            customer=c3,
            defaults={
                'follow_up_date': today - timedelta(days=8),
                'follow_up_type': 'Call',
                'status': 'Completed',
                'assigned_to': sales2,
                'remarks': 'Client expressed high satisfaction with rollout schedule.'
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ Sample Follow-Ups created."))

        # 7. Create Activities
        Activity.objects.get_or_create(
            subject='Discovery Zoom with IT Leadership',
            customer=c1,
            defaults={
                'activity_type': 'Meeting',
                'description': 'Reviewed technical prerequisites and active security compliance standards.',
                'assigned_to': sales1,
                'status': 'Completed'
            }
        )

        Activity.objects.get_or_create(
            subject='Contract negotiation phone conference',
            customer=c2,
            defaults={
                'activity_type': 'Call',
                'description': 'Discussed multi-year maintenance terms and billing schedule.',
                'assigned_to': sales1,
                'status': 'Completed'
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ Sample Activities created."))

        # 8. Create Audit Logs
        AuditLog.log(
            action='LOGIN',
            entity_name='Auth',
            record_id=str(admin_user.id),
            user=admin_user,
            result='SUCCESS',
            details='Administrator logged into AcxiomCRM portal.'
        )

        AuditLog.log(
            action='CREATE',
            entity_name='Customer',
            record_id=str(c1.id),
            user=admin_user,
            result='SUCCESS',
            details=f"Customer '{c1.name}' registered into database."
        )

        AuditLog.log(
            action='STATUS_CHANGE',
            entity_name='Opportunity',
            record_id=str(o3.id),
            user=sales2,
            result='SUCCESS',
            details=f"Opportunity '{o3.name}' stage transitioned to Won ($95,000.00)."
        )

        self.stdout.write(self.style.SUCCESS("✓ Audit logs generated."))
        self.stdout.write(self.style.SUCCESS("=== AcxiomCRM Database Successfully Seeded! ==="))
