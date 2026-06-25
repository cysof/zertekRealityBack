# account/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, AgentProfile, AffiliateProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'phone',
            'bvn',
            'nin',
            'address',
            'password',
            'password2'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')

        bvn = validated_data.get('bvn') or None
        nin = validated_data.get('nin') or None

        user = User.objects.create(
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            bvn=bvn,
            nin=nin,
            address=validated_data.get('address', ''),
            role=validated_data.get('role', User.role.field.default),
        )
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()  # ← added

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'bvn',
            'nin',
            'address',
            'role',
            'is_verified',
            'is_affiliate',
            'profile_image',
            'image_url',  # ← added
            'date_joined'
        ]
        read_only_fields = [
            'id', 'role', 'is_verified', 'is_affiliate', 'bvn', 'nin', 'date_joined'
        ]

    def get_full_name(self, obj):
        return obj.full_name

    def get_image_url(self, obj):
        if obj.profile_image:
            return obj.profile_image.url
        return None


class AgentApplicationSerializer(serializers.Serializer):
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    years_experience = serializers.IntegerField(required=False, min_value=0, default=0)
    specialization = serializers.CharField(
        required=False, allow_blank=True, max_length=200, default=''
    )
    cv = serializers.FileField(required=False, allow_null=True)
    facebook_url = serializers.URLField(required=False, allow_blank=True, default='')
    instagram_url = serializers.URLField(required=False, allow_blank=True, default='')
    twitter_url = serializers.URLField(required=False, allow_blank=True, default='')
    linkedin_url = serializers.URLField(required=False, allow_blank=True, default='')
    whatsapp_url = serializers.URLField(required=False, allow_blank=True, default='')


class AffiliateApplicationSerializer(serializers.Serializer):
    pass


class PublicAgentUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()  # ← added

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'profile_image', 'image_url']  # ← added

    def get_full_name(self, obj):
        return obj.full_name

    def get_image_url(self, obj):
        if obj.profile_image:
            return obj.profile_image.url
        return None


class AgentProfileSerializer(serializers.ModelSerializer):
    user = PublicAgentUserSerializer(read_only=True)
    initials = serializers.ReadOnlyField()
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = AgentProfile
        fields = [
            'id',
            'user',
            'initials',
            'profile_picture_url',
            'bio',
            'years_experience',
            'specialization',
            'cv',
            'is_approved',
            'commission_rate',
            'facebook_url',
            'instagram_url',
            'twitter_url',
            'linkedin_url',
            'whatsapp_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_approved', 'commission_rate', 'created_at', 'updated_at']

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            return obj.profile_picture.url
        return None


class AffiliateProfileSerializer(serializers.ModelSerializer):
    user = PublicAgentUserSerializer(read_only=True)
    referral_link = serializers.ReadOnlyField()

    class Meta:
        model = AffiliateProfile
        fields = [
            'id',
            'user',
            'referral_code',
            'referral_link',
            'total_referrals',
            'total_commission_earned',
            'pending_commission',
            'commission_rate',
            'is_approved',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'referral_code', 'total_referrals', 'total_commission_earned',
            'pending_commission', 'commission_rate', 'is_approved',
            'created_at', 'updated_at',
        ]