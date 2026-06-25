# api/models.py
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from cloudinary.models import CloudinaryField
from account.models import User, AgentProfile

DOCUMENT_TYPE = [
    ('co', 'C of O'),
    ('ro', 'R of O')
]


class Property(models.Model):
    """
    Property model for real estate listings (For Sale only)
    """
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
    )

    title = models.CharField(max_length=200)
    location = models.CharField(max_length=100)
    address = models.TextField()
    price = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    title_document = models.CharField(max_length=16, choices=DOCUMENT_TYPE)
    sqft = models.IntegerField(validators=[MinValueValidator(0)])
    is_new = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    image = CloudinaryField('image', folder='zertek/properties/', null=True, blank=True)
    description = models.TextField()
    amenities = models.JSONField(default=list)

    # Listing agent — points directly at the agent's account profile.
    # No more separate `api.Agent` model duplicating user/contact info.
    agent = models.ForeignKey(
        AgentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='properties'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return self.title


class Inquiry(models.Model):
    """
    Inquiry model for property viewing requests
    """
    STATUS_CHOICES = (
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('inspection_scheduled', 'Inspection Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    property_listing = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='inquiries')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inquiries')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField()
    inspection_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} - {self.property_listing.title}"


class LandBankingPlan(models.Model):
    """
    Payment plans available for land banking
    """
    name = models.CharField(max_length=100)
    duration_months = models.IntegerField(validators=[MinValueValidator(1)])
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0)]
    )
    down_payment_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=20.00,
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['duration_months']

    def __str__(self):
        return f"{self.name} - {self.duration_months} months - {self.interest_rate}% interest"


class LandBankingAgreement(models.Model):
    """
    Agreement between Zertek Realty and buyer for installment payment
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
        ('cancelled', 'Cancelled'),
    )

    agreement_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='land_banking_agreements')

    # PROTECT, not CASCADE: a financial/legal record must not vanish if the
    # buyer's account is deleted. Deletion will be blocked while agreements exist.
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='land_banking_agreements')

    buyer_name = models.CharField(max_length=200)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=20)

    plan = models.ForeignKey(LandBankingPlan, on_delete=models.PROTECT)
    total_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    down_payment = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    total_payable = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    balance_remaining = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])

    start_date = models.DateField()
    end_date = models.DateField()
    next_payment_date = models.DateField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    default_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    agreement_document = models.FileField(
        upload_to='agreements/documents/', max_length=2000, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['next_payment_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['property'],
                condition=models.Q(status__in=['pending', 'active']),
                name='unique_active_agreement_per_property',
            )
        ]

    def __str__(self):
        return f"{self.agreement_id} - {self.buyer_name} - {self.property.title}"


class Payment(models.Model):
    """
    Individual payment records for land banking
    """
    PAYMENT_METHODS = (
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card Payment'),
        ('ussd', 'USSD'),
        ('wallet', 'Wallet'),
    )

    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )

    agreement = models.ForeignKey(LandBankingAgreement, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    payment_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.agreement.agreement_id} - ₦{self.amount} - {self.status}"


class PaymentReminder(models.Model):
    """
    Track reminders sent to buyers
    """
    REMINDER_TYPES = (
        ('upcoming', 'Upcoming Payment'),
        ('overdue', 'Overdue Payment'),
        ('final_warning', 'Final Warning'),
        ('default_notice', 'Default Notice'),
    )

    agreement = models.ForeignKey(LandBankingAgreement, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    sent_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-sent_date']

    def __str__(self):
        return f"{self.agreement.agreement_id} - {self.reminder_type} - {self.sent_date}"