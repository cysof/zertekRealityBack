# agent/serializers.py
from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.validators import MinValueValidator
from rest_framework import serializers
from account.models import AgentProfile
from account.serializers import AgentProfileSerializer
from .models import (
    Property, Inquiry, LandBankingPlan,
    LandBankingAgreement, Payment, PaymentReminder
)


class PropertyListSerializer(serializers.ModelSerializer):
    """
    Lightweight property serializer for list views
    """
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    agent_initials = serializers.CharField(source='agent.initials', read_only=True)
    image_url = serializers.SerializerMethodField()
    price_label = serializers.SerializerMethodField()
    property_type = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id',
            'title',
            'location',
            'price',
            'price_label',
            'property_type',
            'sqft',
            'is_new',
            'is_featured',
            'status',
            'image_url',
            'agent_name',
            'agent_initials',
            'created_at'
        ]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_price_label(self, obj):
        if obj.price >= 1000000:
            return f"₦{obj.price/1000000:,.1f}M"
        return f"₦{obj.price:,.0f}"

    def get_property_type(self, obj):
        return "For Sale"


class PropertySerializer(serializers.ModelSerializer):
    """
    Full property serializer with agent details
    """
    agent = AgentProfileSerializer(read_only=True)
    agent_id = serializers.PrimaryKeyRelatedField(
        queryset=AgentProfile.objects.all(),
        source='agent',
        write_only=True,
        required=False
    )
    image_url = serializers.SerializerMethodField()
    price_label = serializers.SerializerMethodField()
    property_type = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id',
            'title',
            'location',
            'address',
            'price',
            'price_label',
            'property_type',
            'title_document',
            'sqft',
            'is_new',
            'is_featured',
            'status',
            'image',
            'image_url',
            'description',
            'amenities',
            'agent',
            'agent_id',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def get_price_label(self, obj):
        if obj.price >= 1000000:
            return f"₦{obj.price/1000000:,.1f}M"
        return f"₦{obj.price:,.0f}"

    def get_property_type(self, obj):
        return "For Sale"


class InquirySerializer(serializers.ModelSerializer):
    """
    Inquiry serializer for list/detail views
    """
    property_title = serializers.CharField(source='property_listing.title', read_only=True)
    property_location = serializers.CharField(source='property_listing.location', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Inquiry
        fields = [
            'id',
            'property_listing',
            'property_title',
            'property_location',
            'user',
            'user_email',
            'user_name',
            'name',
            'email',
            'phone',
            'message',
            'inspection_date',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InquiryCreateSerializer(serializers.ModelSerializer):
    """
    Inquiry serializer for create/view (public submission)
    """
    class Meta:
        model = Inquiry
        fields = [
            'property_listing',
            'name',
            'email',
            'phone',
            'message',
            'inspection_date'
        ]
    # No extra `validate()` needed here — `property_listing` is already a
    # PrimaryKeyRelatedField, so DRF rejects a nonexistent id at the field
    # level before validate() ever runs. A manual existence re-check was
    # redundant dead code.


class LandBankingPlanSerializer(serializers.ModelSerializer):
    """
    Land banking plan serializer
    """
    class Meta:
        model = LandBankingPlan
        fields = [
            'id',
            'name',
            'duration_months',
            'interest_rate',
            'down_payment_percentage',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LandBankingAgreementSerializer(serializers.ModelSerializer):
    """
    Land banking agreement serializer (read-only for clients)
    """
    property_title = serializers.CharField(source='property.title', read_only=True)
    property_location = serializers.CharField(source='property.location', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    percentage_complete = serializers.SerializerMethodField()

    class Meta:
        model = LandBankingAgreement
        fields = [
            'id',
            'agreement_id',
            'property',
            'property_title',
            'property_location',
            'user',
            'user_email',
            'user_name',
            'buyer_name',
            'buyer_email',
            'buyer_phone',
            'plan',
            'plan_name',
            'total_price',
            'down_payment',
            'monthly_payment',
            'total_payable',
            'balance_remaining',
            'percentage_complete',
            'start_date',
            'end_date',
            'next_payment_date',
            'status',
            'default_count',
            'agreement_document',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'agreement_id', 'balance_remaining', 'percentage_complete',
            'created_at', 'updated_at', 'status', 'default_count'
        ]

    def get_percentage_complete(self, obj):
        # total_payable (not total_price) is the correct denominator —
        # for interest-bearing plans total_payable > total_price, and using
        # total_price would understate how much is actually still owed.
        if obj.total_payable > 0:
            paid = obj.total_payable - obj.balance_remaining
            return round((paid / obj.total_payable) * 100, 2)
        return 0


class LandBankingAgreementCreateSerializer(serializers.ModelSerializer):
    """
    Land banking agreement serializer for creation
    """
    class Meta:
        model = LandBankingAgreement
        fields = [
            'property',
            'plan',
            'buyer_name',
            'buyer_email',
            'buyer_phone',
        ]

    def validate(self, data):
        property_obj = data['property']

        if property_obj.status != 'available':
            raise serializers.ValidationError("Property is not available for land banking")

        if LandBankingAgreement.objects.filter(
            property=property_obj,
            status__in=['pending', 'active']
        ).exists():
            raise serializers.ValidationError("This property already has an active agreement")

        return data

    def create(self, validated_data):
        property_obj = validated_data['property']
        plan = validated_data['plan']

        total_price = property_obj.price
        down_payment = (plan.down_payment_percentage / 100) * total_price

        # Interest applies only to the financed balance (what's left after
        # the down payment) — not the full price. Charging interest on
        # money the buyer already paid upfront would overcharge them.
        financed_amount = total_price - down_payment

        if plan.interest_rate > 0:
            interest_amount = financed_amount * (plan.interest_rate / 100)
            financed_with_interest = financed_amount + interest_amount
            monthly_payment = financed_with_interest / plan.duration_months
            total_payable = down_payment + financed_with_interest
            balance_remaining = financed_with_interest
        else:
            monthly_payment = financed_amount / plan.duration_months
            total_payable = total_price
            balance_remaining = financed_amount

        # balance_remaining + down_payment == total_payable always holds
        # here, so payments correctly converge the balance to zero in line
        # with what was actually promised to the buyer.

        start_date = date.today()
        # relativedelta (calendar months), not a fixed 30-day approximation —
        # must match the month-advancement logic used in make_payment, or
        # next_payment_date and end_date drift out of sync over the life
        # of the agreement.
        end_date = start_date + relativedelta(months=plan.duration_months)
        next_payment_date = start_date + relativedelta(months=1)

        agreement = LandBankingAgreement.objects.create(
            property=property_obj,
            user=self.context['request'].user,
            buyer_name=validated_data['buyer_name'],
            buyer_email=validated_data['buyer_email'],
            buyer_phone=validated_data['buyer_phone'],
            plan=plan,
            total_price=total_price,
            down_payment=down_payment,
            monthly_payment=monthly_payment,
            total_payable=total_payable,
            balance_remaining=balance_remaining,
            start_date=start_date,
            end_date=end_date,
            next_payment_date=next_payment_date,
            status='pending'
        )

        property_obj.status = 'reserved'
        property_obj.save(update_fields=['status'])

        return agreement


class PaymentSerializer(serializers.ModelSerializer):
    """
    Payment serializer
    """
    agreement_id = serializers.UUIDField(source='agreement.agreement_id', read_only=True)
    property_title = serializers.CharField(source='agreement.property.title', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'agreement',
            'agreement_id',
            'property_title',
            'amount',
            'payment_date',
            'due_date',
            'payment_method',
            'reference',
            'status',
            'notes',
            'created_at'
        ]
        read_only_fields = ['id', 'payment_date', 'created_at']


class PaymentCreateSerializer(serializers.Serializer):
    """
    Payment creation serializer
    """
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_method = serializers.ChoiceField(choices=Payment.PAYMENT_METHODS)
    reference = serializers.CharField(max_length=100)
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentReminderSerializer(serializers.ModelSerializer):
    """
    Payment reminder serializer
    """
    agreement_id = serializers.UUIDField(source='agreement.agreement_id', read_only=True)
    buyer_name = serializers.CharField(source='agreement.buyer_name', read_only=True)

    class Meta:
        model = PaymentReminder
        fields = [
            'id',
            'agreement',
            'agreement_id',
            'buyer_name',
            'reminder_type',
            'sent_date',
            'due_date',
            'message',
            'is_read',
            'created_at'
        ]
        read_only_fields = ['id', 'sent_date', 'created_at']