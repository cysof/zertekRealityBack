# api/views.py
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.db import transaction, IntegrityError
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import (
    Property, Inquiry, LandBankingPlan,
    LandBankingAgreement, Payment, PaymentReminder
)
from .serializers import (
    PropertySerializer, PropertyListSerializer,
    InquirySerializer, InquiryCreateSerializer,
    LandBankingPlanSerializer,
    LandBankingAgreementSerializer, LandBankingAgreementCreateSerializer,
    PaymentSerializer, PaymentCreateSerializer,
    PaymentReminderSerializer
)
from .permissions import (
    IsStaffOrApprovedAgent, IsStaffOrReadOnly, InquiryPermission, IsStaffOnly
)

from django.core.mail import send_mail
from django.conf import settings




class PropertyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Property CRUD operations.
    Read: public. Write: staff or an approved agent (own listings only).
    """
    queryset = Property.objects.all()
    permission_classes = [IsStaffOrApprovedAgent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['location', 'status', 'is_new', 'is_featured']
    search_fields = ['title', 'location', 'address', 'description']
    ordering_fields = ['price', 'created_at', 'sqft']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        return PropertySerializer

    def perform_create(self, serializer):
        """
        Auto-assign the listing agent from the requesting user — never trust
        a client-supplied `agent` id, or any authenticated user could list a
        property under someone else's agent profile. Staff may still pass
        `agent` explicitly (e.g. creating a listing on behalf of an agent).
        """
        user = self.request.user
        if user.is_staff:
            serializer.save()
        else:
            serializer.save(agent=user.agent_profile)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured properties"""
        featured_properties = self.get_queryset().filter(is_featured=True)
        serializer = PropertyListSerializer(featured_properties, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def new(self, request):
        """Get new properties"""
        new_properties = self.get_queryset().filter(is_new=True)
        serializer = PropertyListSerializer(new_properties, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available properties"""
        available_properties = self.get_queryset().filter(status='available')
        serializer = PropertyListSerializer(available_properties, many=True)
        return Response(serializer.data)


class InquiryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Inquiry CRUD operations.
    Create: open to everyone (guests can submit inquiries).
    Read/Update/Delete: authenticated, restricted to staff or the listing's agent.
    """
    queryset = Inquiry.objects.all()
    permission_classes = [InquiryPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'property_listing']
    search_fields = ['name', 'email', 'phone', 'message']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return InquiryCreateSerializer
        return InquirySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.is_staff:
            return queryset
        if hasattr(user, 'agent_profile') and user.agent_profile.is_approved:
            return queryset.filter(property_listing__agent=user.agent_profile)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        """Public submission — works for both guests and authenticated users."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.is_authenticated:
            serializer.save(user=request.user)
        else:
            serializer.save()

        return Response(
            {'message': 'Inquiry submitted successfully! We will contact you soon.'},
            status=status.HTTP_201_CREATED
        )


class LandBankingPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LandBankingPlan CRUD operations.
    Read: public. Write: staff only — payment terms must not be publicly editable.
    """
    queryset = LandBankingPlan.objects.filter(is_active=True)
    serializer_class = LandBankingPlanSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ['duration_months', 'interest_rate']
    ordering = ['duration_months']


class LandBankingAgreementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LandBankingAgreement CRUD operations
    """
    queryset = LandBankingAgreement.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'property', 'user']
    search_fields = ['buyer_name', 'buyer_email']
    ordering_fields = ['created_at', 'next_payment_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return LandBankingAgreementCreateSerializer
        return LandBankingAgreementSerializer

    def get_queryset(self):
        """Filter agreements based on user role"""
        queryset = super().get_queryset()
        user = self.request.user

        if user.is_staff:
            return queryset

        if hasattr(user, 'agent_profile') and user.agent_profile.is_approved:
            agent_properties = user.agent_profile.properties.values_list('id', flat=True)
            return queryset.filter(property__id__in=agent_properties)

        return queryset.filter(user=user)

    def create(self, request, *args, **kwargs):
        """
        Force `user` to the requester via serializer context — never trust
        a client-supplied user id. Availability checks and reserving the
        property both live in LandBankingAgreementCreateSerializer.validate()
        /.create(); duplicating that logic here would risk the two drifting
        out of sync. We just need to (a) ensure context carries the request
        so the serializer can pull request.user, and (b) turn the DB-level
        duplicate-active-agreement race into a clean 400 instead of a 500.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                agreement = serializer.save()
        except IntegrityError:
            return Response(
                {'error': 'This property already has an active agreement.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            LandBankingAgreementSerializer(agreement).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def make_payment(self, request, pk=None):
        """Make a payment on an agreement"""
        agreement = self.get_object()

        if agreement.status != 'active':
            return Response(
                {'error': 'Payment cannot be made on a non-active agreement'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PaymentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Lock the agreement row so two concurrent payments can't
                # both read the same stale balance_remaining and lose an update.
                agreement = (
                    LandBankingAgreement.objects.select_for_update().get(pk=agreement.pk)
                )

                payment = Payment.objects.create(
                    agreement=agreement,
                    amount=serializer.validated_data['amount'],
                    due_date=agreement.next_payment_date,
                    payment_method=serializer.validated_data['payment_method'],
                    reference=serializer.validated_data['reference'],
                    notes=serializer.validated_data.get('notes', ''),
                )

                new_balance = agreement.balance_remaining - payment.amount
                agreement.balance_remaining = max(new_balance, 0)

                if agreement.balance_remaining <= 0:
                    agreement.status = 'completed'
                else:
                    # Advance the next due date by the plan's payment cycle
                    # (monthly) — otherwise next_payment_date never moves
                    # forward and reminders/overdue checks break.
                    from dateutil.relativedelta import relativedelta
                    agreement.next_payment_date = agreement.next_payment_date + relativedelta(months=1)

                agreement.save(update_fields=['balance_remaining', 'status', 'next_payment_date', 'updated_at'])
        except IntegrityError:
            return Response(
                {'error': 'A payment with this reference already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'message': 'Payment recorded successfully',
            'payment': PaymentSerializer(payment).data,
            'balance_remaining': agreement.balance_remaining
        }, status=status.HTTP_201_CREATED)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Payment — read-only for clients/agents, staff-only writes.
    Regular payment creation must go through
    LandBankingAgreementViewSet.make_payment, which enforces balance
    updates, agreement-status checks, and locking. Allowing direct POST
    here for ordinary users would let them fabricate confirmed payments
    on any agreement.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsStaffOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'agreement']
    ordering_fields = ['payment_date', 'due_date']
    ordering = ['-payment_date']

    def get_queryset(self):
        """Filter payments based on user role"""
        queryset = super().get_queryset()
        user = self.request.user

        if user.is_staff:
            return queryset

        if hasattr(user, 'agent_profile') and user.agent_profile.is_approved:
            agent_properties = user.agent_profile.properties.values_list('id', flat=True)
            return queryset.filter(agreement__property__id__in=agent_properties)

        return queryset.filter(agreement__user=user)


class PaymentReminderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PaymentReminder CRUD operations
    """
    queryset = PaymentReminder.objects.all()
    serializer_class = PaymentReminderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['agreement', 'reminder_type', 'is_read']
    ordering_fields = ['sent_date', 'due_date']
    ordering = ['-sent_date']

    def get_queryset(self):
        """Filter reminders based on user role"""
        queryset = super().get_queryset()
        user = self.request.user

        if user.is_staff:
            return queryset

        return queryset.filter(agreement__user=user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a reminder as read"""
        reminder = self.get_object()
        reminder.is_read = True
        reminder.save(update_fields=['is_read'])
        return Response({'message': 'Reminder marked as read'})


class AgentPropertyStatsView(APIView):
    """
    Get statistics for an agent's properties
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'agent_profile'):
            return Response(
                {'error': 'User is not an agent'},
                status=status.HTTP_400_BAD_REQUEST
            )

        agent_profile = request.user.agent_profile
        properties = Property.objects.filter(agent=agent_profile)

        stats = {
            'total_listings': properties.count(),
            'available': properties.filter(status='available').count(),
            'reserved': properties.filter(status='reserved').count(),
            'sold': properties.filter(status='sold').count(),
            'featured': properties.filter(is_featured=True).count(),
            'total_value': properties.aggregate(total=Sum('price'))['total'] or 0,
        }

        return Response(stats)
    


class ContactMessageView(APIView):
    permission_classes = []

    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        phone = request.data.get('phone', 'N/A')
        subject = request.data.get('subject')
        message = request.data.get('message')

        if not all([name, email, subject, message]):
            return Response({'detail': 'All required fields must be filled.'}, status=400)

        send_mail(
            subject=f"Zertek Realty Home: {subject}",
            message=f"Name: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['salesteam.zertekrealtyhomeltd@gmail.com','zertekrealityhome@gmail.com'],
            fail_silently=False,
        )
        return Response({'detail': 'Message sent successfully.'}, status=200)