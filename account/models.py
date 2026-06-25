# account/models.py
import uuid
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.contrib.auth.models import AbstractUser, BaseUserManager
from cloudinary.models import CloudinaryField

ROLE_CHOICES = (
    ('client', 'Client'),
    ('agent', 'Agent'),
    ('affiliate', 'Affiliate'),
)

bvn_validator = RegexValidator(regex=r'^\d{11}$', message='BVN must be exactly 11 digits.')
nin_validator = RegexValidator(regex=r'^\d{11}$', message='NIN must be exactly 11 digits.')


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for Zertek Realty
    """
    # Remove username - use email as unique identifier
    username = None
    email = models.EmailField(unique=True)

    # Basic Info
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)

    # KYC (Know Your Customer)
    bvn = models.CharField(
        max_length=11, blank=True, null=True, unique=True,
        validators=[bvn_validator]
    )
    nin = models.CharField(
        max_length=11, blank=True, null=True, unique=True,
        validators=[nin_validator]
    )

    # Role
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')

    # Status
    is_verified = models.BooleanField(default=False)
    is_affiliate = models.BooleanField(default=False)

    # Profile Image
    profile_image = CloudinaryField('image', folder='zertek/users/', null=True, blank=True)

    # Timestamps
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use custom manager
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone']

    class Meta:
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class AgentProfile(models.Model):
    """
    Extended profile for Agents
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    profile_picture = CloudinaryField('image', folder='zertek/agents/', null=True, blank=True)

    # Professional Info
    bio = models.TextField(blank=True)
    years_experience = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    specialization = models.CharField(max_length=200, blank=True)

    # Certifications
    cv = models.FileField(upload_to='agents/cv/', max_length=2000, blank=True, null=True)

    # Status
    is_approved = models.BooleanField(default=False)
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=10.00,
        validators=[MinValueValidator(0)]
    )

    # Social Links
    facebook_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    whatsapp_url = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__first_name']

    def __str__(self):
        return f"{self.user.full_name} - Agent"

    @property
    def initials(self):
        parts = self.user.full_name.split()
        return ''.join([word[0].upper() for word in parts[:2]]) if parts else ''

    @property
    def name(self):
        return self.user.full_name

    @property
    def phone(self):
        return self.user.phone

    @property
    def email(self):
        return self.user.email

    @property
    def image(self):
        return self.user.profile_image


class AffiliateProfile(models.Model):
    """
    Extended profile for Affiliates
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='affiliate_profile')

    # Referral Info
    referral_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    total_referrals = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_commission_earned = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )
    pending_commission = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )

    # Commission Settings
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.00,
        validators=[MinValueValidator(0)]
    )

    # Status
    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__first_name']

    def __str__(self):
        return f"{self.user.full_name} - Affiliate"

    @property
    def referral_link(self):
        return f"/?ref={self.referral_code}"


class Referral(models.Model):
    """
    Track referrals made by affiliates
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='referrals')
    referred_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referred_by')

    # Referral Details
    referral_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Commission
    commission_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )
    is_commission_paid = models.BooleanField(default=False)
    paid_date = models.DateTimeField(null=True, blank=True)

    # Tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-referral_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_commission_paid']),
        ]

    def __str__(self):
        return f"{self.affiliate.user.email} -> {self.referred_user.email}"