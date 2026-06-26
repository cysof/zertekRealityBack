# agent/admin.py
from django.contrib import admin
from django import forms
from django.db import models
from .models import (
    Property, Inquiry, LandBankingPlan,
    LandBankingAgreement, Payment, PaymentReminder
)
from django.utils.html import format_html


class PropertyAdminForm(forms.ModelForm):
    """Custom form for Property admin with human-readable amenities"""

    amenities = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'cols': 50,
            'style': 'width: 100%; font-family: monospace;',
            'placeholder': 'Enter each amenity on a new line (e.g.\nSwimming Pool\n2 Car Garage\n24/7 Security)'
        }),
        required=False,
        help_text='Enter each amenity on a new line. They will be stored as a JSON array.'
    )

    class Meta:
        model = Property
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.amenities:
            if isinstance(self.instance.amenities, list):
                self.initial['amenities'] = '\n'.join(self.instance.amenities)

    def clean_amenities(self):
        """Convert newline-separated text to JSON array"""
        data = self.cleaned_data.get('amenities', '')
        if isinstance(data, str):
            items = [line.strip() for line in data.split('\n') if line.strip()]
            return items
        return data

    def clean_video(self):
        """Enforce 10MB limit at the form level"""
        video = self.cleaned_data.get('video')
        if video and hasattr(video, 'size') and video.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Video file size must not exceed 10MB.')
        return video
    


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    form = PropertyAdminForm
    list_display = ['title', 'location', 'status', 'is_featured', 'is_new']
    search_fields = ['title', 'location', 'address']  # add this
    readonly_fields = ['video_preview']

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'location', 'address', 'description', 'status', 'title_document')
        }),
        ('Details', {
            'fields': ('price', 'sqft', 'amenities', 'is_new', 'is_featured')
        }),
        ('Media', {
            'fields': ('image', 'video', 'video_preview')
        }),
        ('Agent', {
            'fields': ('agent',)
        }),
    )

    def video_preview(self, obj):
        if obj.video:
            return format_html(
                '<video width="400" controls><source src="{}" type="video/mp4"></video>',
                obj.video.url
            )
        return "No video uploaded"
    video_preview.short_description = "Video Preview"



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