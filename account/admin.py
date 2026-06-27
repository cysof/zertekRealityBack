# account/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html
from django import forms
from .models import User, AgentProfile, AffiliateProfile, Referral


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'role')


class CustomUserChangeForm(UserChangeForm):
    role = forms.ChoiceField(
        choices=User.role.field.choices,
        widget=forms.Select,
        required=True,
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    list_display = ['first_name', 'last_name', 'bvn', 'nin', 'phone', 'role', 'is_verified', 'date_joined']
    list_filter = ['role', 'is_verified', 'is_active', 'is_affiliate']
    list_editable = ['is_verified']  # ← role removed from list_editable, change via AgentProfile approval
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'address')}),
        ('KYC', {'fields': ('bvn', 'nin')}),
        ('Role & Status', {'fields': ('role', 'is_verified', 'is_affiliate')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Profile', {'fields': ('profile_image',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone', 'role', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['date_joined', 'last_login']


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ['user','get_bvn', 'get_nin','image_preview', 'is_approved', 'commission_rate', 'created_at']
    list_filter = ['is_approved', 'years_experience']
    actions = ['approve_agents', 'revoke_agents']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'specialization']
    readonly_fields = ['image_preview', 'image_url', 'created_at', 'updated_at']

    
    @admin.display(description='BVN')
    def get_bvn(self, obj):
        return obj.user.bvn

    @admin.display(description='NIN')
    def get_nin(self, obj):
        return obj.user.nin

    @admin.display(description='Email')
    def user_email(self, obj):
        return obj.user.email

    @admin.action(description='✅ Approve selected agents')
    def approve_agents(self, request, queryset):
        for profile in queryset:
            profile.is_approved = True
            profile.save()  # triggers signal → user.role = 'agent'
        self.message_user(request, f'{queryset.count()} agent(s) approved successfully.')

    @admin.action(description='❌ Revoke selected agents')
    def revoke_agents(self, request, queryset):
        for profile in queryset:
            profile.is_approved = False
            profile.save()  # triggers signal → user.role = 'client'
        self.message_user(request, f'{queryset.count()} agent(s) revoked.')

    @admin.display(description='Preview')
    def image_preview(self, obj):
        url = self._get_image_url(obj)
        if url:
            return format_html('<img src="{}" width="40" height="40" style="border-radius:50%;object-fit:cover;" />', url)
        return '—'

    @admin.display(description='Image URL')
    def image_url(self, obj):
        url = self._get_image_url(obj)
        if url:
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return '—'

    def _get_image_url(self, obj):
        if obj.profile_picture:
            return obj.profile_picture.url
        if obj.user.profile_image:
            return obj.user.profile_image.url
        return None


@admin.register(AffiliateProfile)
class AffiliateProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_referrals', 'total_commission_earned', 'is_approved']
    list_filter = ['is_approved']
    actions = ['approve_affiliates', 'revoke_affiliates']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['referral_code', 'created_at', 'updated_at']

    @admin.action(description='✅ Approve selected affiliates')
    def approve_affiliates(self, request, queryset):
        for profile in queryset:
            profile.is_approved = True
            profile.save()  # triggers signal → user.role = 'affiliate'
        self.message_user(request, f'{queryset.count()} affiliate(s) approved successfully.')

    @admin.action(description='❌ Revoke selected affiliates')
    def revoke_affiliates(self, request, queryset):
        for profile in queryset:
            profile.is_approved = False
            profile.save()  # triggers signal → user.role = 'client'
        self.message_user(request, f'{queryset.count()} affiliate(s) revoked.')


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['affiliate', 'referred_user', 'status', 'commission_amount', 'is_commission_paid']
    list_filter = ['status', 'is_commission_paid']
    search_fields = ['affiliate__user__email', 'referred_user__email']
    readonly_fields = ['referral_date', 'created_at', 'updated_at']