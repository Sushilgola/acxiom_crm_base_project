from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from core.models import User, AuditLog
from core.views import get_client_ip
from crm.models import Customer, Lead, Opportunity, FollowUp
from crm.views import get_scoped_queryset, can_manage_record
from .serializers import CustomerDTO, LeadDTO, OpportunityDTO, FollowUpDTO, UserDTO


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        ip = get_client_ip(request)

        if not username or not password:
            return Response({'error': 'Username/email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user_candidate = User.objects.filter(username__iexact=username).first() or \
                         User.objects.filter(email__iexact=username).first()

        if user_candidate and user_candidate.is_locked:
            return Response({
                'error': f"Account locked. Try again in {user_candidate.lockout_minutes_remaining} minutes."
            }, status=status.HTTP_403_FORBIDDEN)

        user = authenticate(request, username=user_candidate.username if user_candidate else username, password=password)

        if user is not None:
            if not user.is_active:
                return Response({'error': 'Account is inactive. Contact administrator.'}, status=status.HTTP_403_FORBIDDEN)

            login(request, user)
            user.reset_failed_logins()

            AuditLog.log(
                action='LOGIN',
                entity_name='Auth',
                record_id=str(user.id),
                user=user,
                user_email=user.email or user.username,
                result='SUCCESS',
                ip_address=ip,
                details=f"REST API login successful for {user.username}."
            )

            serializer = UserDTO(user)
            return Response({
                'message': 'Login successful',
                'user': serializer.data,
            }, status=status.HTTP_200_OK)
        else:
            if user_candidate:
                user_candidate.record_failed_login()
                remaining = max(0, 5 - user_candidate.failed_login_count)
            else:
                remaining = 0

            AuditLog.log(
                action='FAILED_LOGIN',
                entity_name='Auth',
                user_email=username,
                result='FAILURE',
                ip_address=ip,
                details=f"Failed REST API login for '{username}'."
            )

            return Response({
                'error': 'Invalid username or password',
                'remaining_attempts': remaining,
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        AuditLog.log(
            action='LOGOUT',
            entity_name='Auth',
            record_id=str(user.id),
            user=user,
            result='SUCCESS',
            ip_address=get_client_ip(request),
            details=f"REST API logout for {user.username}."
        )
        logout(request)
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


# ==========================================
# CUSTOMER API
# ==========================================
class CustomerListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = get_scoped_queryset(request.user, Customer.objects.all())
        search_q = request.query_params.get('q', '').strip()
        if search_q:
            qs = qs.filter(
                Q(name__icontains=search_q) |
                Q(email__icontains=search_q) |
                Q(phone__icontains=search_q) |
                Q(company_name__icontains=search_q) |
                Q(customer_code__icontains=search_q)
            )
        serializer = CustomerDTO(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CustomerDTO(data=request.data)
        if serializer.is_valid():
            assigned_to = serializer.validated_data.get('assigned_to')
            if not assigned_to:
                assigned_to = request.user
            customer = serializer.save(assigned_to=assigned_to)

            AuditLog.log(
                action='CREATE',
                entity_name='Customer',
                record_id=str(customer.id),
                user=request.user,
                new_value=serializer.data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Customer '{customer.name}' created via REST API."
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        customer = get_object_or_404(Customer, pk=pk)
        if not can_manage_record(user, customer):
            return None
        return customer

    def get(self, request, pk):
        customer = self.get_object(pk, request.user)
        if customer is None:
            return Response({'error': 'Permission denied or not found.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = CustomerDTO(customer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        customer = self.get_object(pk, request.user)
        if customer is None:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        old_data = CustomerDTO(customer).data
        serializer = CustomerDTO(customer, data=request.data, partial=True)
        if serializer.is_valid():
            updated_customer = serializer.save()
            AuditLog.log(
                action='UPDATE',
                entity_name='Customer',
                record_id=str(updated_customer.id),
                user=request.user,
                old_value=old_data,
                new_value=serializer.data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Customer '{updated_customer.name}' updated via REST API."
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        customer = self.get_object(pk, request.user)
        if customer is None:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        c_name = customer.name
        AuditLog.log(
            action='DELETE',
            entity_name='Customer',
            record_id=str(customer.id),
            user=request.user,
            old_value={'name': c_name, 'code': customer.customer_code},
            result='SUCCESS',
            ip_address=get_client_ip(request),
            details=f"Customer '{c_name}' deleted via REST API."
        )
        customer.delete()
        return Response({'message': f"Customer '{c_name}' successfully removed."}, status=status.HTTP_200_OK)


# ==========================================
# LEAD API
# ==========================================
class LeadListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = get_scoped_queryset(request.user, Lead.objects.all())
        search_q = request.query_params.get('q', '').strip()
        if search_q:
            qs = qs.filter(
                Q(name__icontains=search_q) |
                Q(company_name__icontains=search_q) |
                Q(email__icontains=search_q) |
                Q(phone__icontains=search_q)
            )
        serializer = LeadDTO(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = LeadDTO(data=request.data)
        if serializer.is_valid():
            assigned_to = serializer.validated_data.get('assigned_to') or request.user
            lead = serializer.save(assigned_to=assigned_to)
            AuditLog.log(
                action='CREATE',
                entity_name='Lead',
                record_id=str(lead.id),
                user=request.user,
                new_value=serializer.data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Lead '{lead.name}' created via REST API."
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# OPPORTUNITY API
# ==========================================
class OpportunityListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = get_scoped_queryset(request.user, Opportunity.objects.all())
        search_q = request.query_params.get('q', '').strip()
        if search_q:
            qs = qs.filter(
                Q(name__icontains=search_q) |
                Q(customer__name__icontains=search_q)
            )
        serializer = OpportunityDTO(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OpportunityDTO(data=request.data)
        if serializer.is_valid():
            assigned_to = serializer.validated_data.get('assigned_to') or request.user
            opp = serializer.save(assigned_to=assigned_to)
            AuditLog.log(
                action='CREATE',
                entity_name='Opportunity',
                record_id=str(opp.id),
                user=request.user,
                new_value=serializer.data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Opportunity '{opp.name}' created via REST API."
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# FOLLOW-UP API
# ==========================================
class FollowUpListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = get_scoped_queryset(request.user, FollowUp.objects.all())
        serializer = FollowUpDTO(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = FollowUpDTO(data=request.data)
        if serializer.is_valid():
            assigned_to = serializer.validated_data.get('assigned_to') or request.user
            followup = serializer.save(assigned_to=assigned_to)
            AuditLog.log(
                action='CREATE',
                entity_name='FollowUp',
                record_id=str(followup.id),
                user=request.user,
                new_value=serializer.data,
                result='SUCCESS',
                ip_address=get_client_ip(request),
                details=f"Follow-up '{followup.subject}' scheduled via REST API."
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# PIPELINE REPORT API
# ==========================================
class PipelineReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Section 10: GET /api/reports/pipeline - Manager/Admin or configured scope
        qs = get_scoped_queryset(request.user, Opportunity.objects.all())

        # Stage breakdown
        stage_summary = []
        for stage_choice in Opportunity.STAGE_CHOICES:
            stage_name = stage_choice[0]
            stage_opps = qs.filter(stage=stage_name)
            count = stage_opps.count()
            total_val = stage_opps.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            weighted_val = sum([o.weighted_amount for o in stage_opps])
            stage_summary.append({
                'stage': stage_name,
                'count': count,
                'total_amount': float(total_val),
                'weighted_amount': float(weighted_val),
            })

        # Owner breakdown
        owner_summary = []
        users = User.objects.filter(is_active=True)
        if request.user.is_sales_role:
            users = users.filter(id=request.user.id)

        for u in users:
            u_opps = qs.filter(assigned_to=u)
            if u_opps.exists():
                u_total = u_opps.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
                owner_summary.append({
                    'owner_id': u.id,
                    'owner_name': u.get_full_name() or u.username,
                    'deal_count': u_opps.count(),
                    'total_amount': float(u_total),
                })

        overall_pipeline = qs.filter(status='Open').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        weighted_pipeline = sum([o.weighted_amount for o in qs.filter(status='Open')])

        return Response({
            'overall_pipeline_value': float(overall_pipeline),
            'weighted_pipeline_value': float(weighted_pipeline),
            'stage_breakdown': stage_summary,
            'owner_breakdown': owner_summary,
        }, status=status.HTTP_200_OK)
