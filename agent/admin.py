# agent/admin.py
from django.contrib import admin
from .models import (
    Property, Inquiry, LandBankingPlan,
    LandBankingAgreement, Payment, PaymentReminder
)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['title', 'location', 'price', 'status', 'is_featured', 'is_new', 'agent', 'created_at']
    list_filter = ['status', 'is_featured', 'is_new', 'title_document']
    search_fields = ['title', 'location', 'address', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    autocomplete_fields = ['agent']


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'property_listing', 'status', 'email', 'phone', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'email', 'phone', 'property_listing__title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    autocomplete_fields = ['property_listing', 'user']


@admin.register(LandBankingPlan)
class LandBankingPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_months', 'interest_rate', 'down_payment_percentage', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['duration_months']


@admin.register(LandBankingAgreement)
class LandBankingAgreementAdmin(admin.ModelAdmin):
    list_display = [
        'agreement_id', 'buyer_name', 'property', 'plan', 'status',
        'balance_remaining', 'next_payment_date', 'default_count',
    ]
    list_filter = ['status', 'plan']
    search_fields = ['agreement_id', 'buyer_name', 'buyer_email', 'property__title']
    # agreement_id, financial totals, and balance are computed at creation
    # time by the serializer — they should never be hand-edited in admin,
    # only adjusted through proper payment/cancellation flows.
    readonly_fields = [
        'agreement_id', 'total_price', 'down_payment', 'monthly_payment',
        'total_payable', 'balance_remaining', 'created_at', 'updated_at',
    ]
    autocomplete_fields = ['property', 'user', 'plan']
    ordering = ['-created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'agreement', 'amount', 'payment_method', 'status', 'due_date', 'payment_date']
    list_filter = ['status', 'payment_method']
    search_fields = ['reference', 'agreement__agreement_id', 'agreement__buyer_name']
    readonly_fields = ['payment_date']
    autocomplete_fields = ['agreement']
    ordering = ['-payment_date']


@admin.register(PaymentReminder)
class PaymentReminderAdmin(admin.ModelAdmin):
    list_display = ['agreement', 'reminder_type', 'due_date', 'sent_date', 'is_read']
    list_filter = ['reminder_type', 'is_read']
    search_fields = ['agreement__agreement_id', 'agreement__buyer_name']
    readonly_fields = ['sent_date']
    autocomplete_fields = ['agreement']
    ordering = ['-sent_date']