# account/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html
from .models import User, AgentProfile, AffiliateProfile, Referral


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'role')


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm

    list_display = ['email', 'first_name', 'last_name', 'phone', 'role', 'is_verified', 'is_active', 'date_joined']
    list_filter = ['role', 'is_verified', 'is_active', 'is_affiliate']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'address')}),
        ('KYC', {'fields': ('bvn', 'nin')}),
        ('Role', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'is_affiliate')}),
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
    list_display = ['user', 'image_preview', 'image_url', 'years_experience', 'specialization', 'is_approved', 'commission_rate']
    list_filter = ['is_approved', 'years_experience']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'specialization']
    readonly_fields = ['image_preview', 'image_url', 'created_at', 'updated_at']

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
        """Prefer AgentProfile.profile_picture, fall back to user.profile_image."""
        if obj.profile_picture:
            return obj.profile_picture.url
        if obj.user.profile_image:
            return obj.user.profile_image.url
        return None


@admin.register(AffiliateProfile)
class AffiliateProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_referrals', 'total_commission_earned', 'is_approved']
    list_filter = ['is_approved']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['referral_code', 'created_at', 'updated_at']


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['affiliate', 'referred_user', 'status', 'commission_amount', 'is_commission_paid']
    list_filter = ['status', 'is_commission_paid']
    search_fields = ['affiliate__user__email', 'referred_user__email']
    readonly_fields = ['referral_date', 'created_at', 'updated_at']