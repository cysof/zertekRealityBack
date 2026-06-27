# account/views.py
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.db import models
from django.core import exceptions as django_exceptions
from .models import User, AgentProfile, AffiliateProfile, Referral
from .serializers import (
    UserRegistrationSerializer, UserSerializer,
    AgentApplicationSerializer, AffiliateApplicationSerializer,
    AgentProfileSerializer, AffiliateProfileSerializer
)


def get_client_ip(request):
    """Best-effort client IP extraction, accounting for reverse proxies."""
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class RegisterView(APIView):
    """
    User registration endpoint.

    `requested_role` (agent/affiliate/client) only controls which profile
    gets created — it does NOT set `user.role`. `user.role` stays 'client'
    until an admin approves the profile (see account/signals.py). This
    keeps the application/approval flow from being bypassable by just
    signing up with a different role.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        requested_role = request.data.get('requested_role', 'client')
        user = serializer.save(role='client')
        message = 'Registration successful!'

        if requested_role == 'agent':
            AgentProfile.objects.create(user=user)
            message = (
                'Registration successful! Your agent application has been '
                'submitted and is awaiting admin approval.'
            )
        elif requested_role == 'affiliate':
            AffiliateProfile.objects.create(user=user)
            message = (
                'Registration successful! Your affiliate application has been '
                'submitted and is awaiting admin approval.'
            )

        refresh = RefreshToken.for_user(user)

        referral_code = request.data.get('referral_code')
        if referral_code:
            try:
                affiliate_profile = AffiliateProfile.objects.get(
                    referral_code=referral_code, is_approved=True
                )
                Referral.objects.create(
                    affiliate=affiliate_profile,
                    referred_user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
                affiliate_profile.total_referrals = models.F('total_referrals') + 1
                affiliate_profile.save(update_fields=['total_referrals'])
            except (AffiliateProfile.DoesNotExist, ValueError, django_exceptions.ValidationError):
                pass

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': message,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    User login endpoint.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class LogoutView(APIView):
    """
    User logout endpoint (blacklist refresh token).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except Exception:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_400_BAD_REQUEST
            )




class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        errors = {}
        user_fields_to_save = []

        phone = request.data.get('phone')
        address = request.data.get('address')
        bvn = request.data.get('bvn')
        nin = request.data.get('nin')

        if phone is not None:
            phone = phone.strip()
            if len(phone) > 20:
                errors['phone'] = 'Phone number must be 20 characters or fewer.'
            else:
                user.phone = phone
                user_fields_to_save.append('phone')

        if address is not None:
            user.address = address.strip()
            user_fields_to_save.append('address')

        # BVN — one-time only
        if bvn is not None:
            if user.bvn:
                errors['bvn'] = 'BVN has already been set and cannot be changed.'
            else:
                user.bvn = bvn.strip()
                user_fields_to_save.append('bvn')

        # NIN — one-time only
        if nin is not None:
            if user.nin:
                errors['nin'] = 'NIN has already been set and cannot be changed.'
            else:
                user.nin = nin.strip()
                user_fields_to_save.append('nin')

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        if user_fields_to_save:
            user.save(update_fields=user_fields_to_save)

        # Profile picture
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            if user.role == 'agent' and hasattr(user, 'agent_profile'):
                user.agent_profile.profile_picture = profile_picture
                user.agent_profile.save(update_fields=['profile_picture'])
            elif user.role == 'affiliate' and hasattr(user, 'affiliate_profile'):
                user.affiliate_profile.profile_picture = profile_picture
                user.affiliate_profile.save(update_fields=['profile_picture'])
            else:
                user.profile_image = profile_picture
                user.save(update_fields=['profile_image'])

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class AgentSocialProfileUpdateView(APIView):
    """
    PATCH /api/account/agent-profile/
    Lets an approved agent update their bio, social links, etc.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agent_profile = get_object_or_404(AgentProfile, user=request.user)
        return Response(AgentProfileSerializer(agent_profile).data)

    def patch(self, request):
        agent_profile = get_object_or_404(AgentProfile, user=request.user)

        editable_fields = [
            'bio', 'years_experience', 'specialization',
            'facebook_url', 'instagram_url', 'twitter_url',
            'linkedin_url', 'whatsapp_url',
        ]

        for field in editable_fields:
            if field in request.data:
                setattr(agent_profile, field, request.data[field])

        # CV file upload
        if 'cv' in request.FILES:
            agent_profile.cv = request.FILES['cv']

        agent_profile.save()
        return Response(AgentProfileSerializer(agent_profile).data, status=status.HTTP_200_OK)
    

class ApplyAgentView(APIView):
    """
    Apply to become an agent (for users who registered as 'client' and
    later decide to apply, rather than requesting it at signup).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if hasattr(request.user, 'agent_profile'):
            return Response(
                {'error': 'You already have an agent profile'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AgentApplicationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        agent_profile = AgentProfile.objects.create(
            user=request.user,
            bio=serializer.validated_data.get('bio', ''),
            years_experience=serializer.validated_data.get('years_experience', 0),
            specialization=serializer.validated_data.get('specialization', ''),
            cv=serializer.validated_data.get('cv'),
            facebook_url=serializer.validated_data.get('facebook_url', ''),
            instagram_url=serializer.validated_data.get('instagram_url', ''),
            twitter_url=serializer.validated_data.get('twitter_url', ''),
            linkedin_url=serializer.validated_data.get('linkedin_url', ''),
            whatsapp_url=serializer.validated_data.get('whatsapp_url', ''),
        )

        return Response({
            'message': 'Agent application submitted successfully! Please wait for admin approval.',
            'agent_profile': AgentProfileSerializer(agent_profile).data
        }, status=status.HTTP_201_CREATED)


class ApplyAffiliateView(APIView):
    """
    Apply to become an affiliate.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if hasattr(request.user, 'affiliate_profile'):
            return Response(
                {'error': 'You already have an affiliate profile'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AffiliateApplicationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        affiliate_profile = AffiliateProfile.objects.create(
            user=request.user
        )

        return Response({
            'message': 'Affiliate application submitted successfully! Please wait for admin approval.',
            'affiliate_profile': AffiliateProfileSerializer(affiliate_profile).data
        }, status=status.HTTP_201_CREATED)


class AgentProfileView(APIView):
    """
    Get agent profile (for public viewing) — approved agents only.
    """
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id, role='agent')
        agent_profile = get_object_or_404(AgentProfile, user=user, is_approved=True)
        serializer = AgentProfileSerializer(agent_profile)
        return Response(serializer.data)


class AffiliateProfileView(APIView):
    """
    Get affiliate profile (for public viewing) — approved affiliates only.
    """
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id, role='affiliate')
        affiliate_profile = get_object_or_404(AffiliateProfile, user=user, is_approved=True)
        serializer = AffiliateProfileSerializer(affiliate_profile)
        return Response(serializer.data)


class AgentListView(APIView):
    """
    Get list of all approved agents (public).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        agents = AgentProfile.objects.filter(is_approved=True)
        serializer = AgentProfileSerializer(agents, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# AgentProfileUpdateView is kept as a strict agent-only alias in case you
# need a separate endpoint scoped to /api/agent/profile/. It delegates to
# the same logic but enforces the agent guard explicitly.
# ---------------------------------------------------------------------------
class AgentProfileUpdateView(APIView):
    """
    PATCH /api/agent/profile/

    Strict alias of UserProfileUpdateView scoped to approved agents only.
    Clients and affiliates will get 404 here — direct them to
    PATCH /api/account/profile/ instead.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user

        # Hard guard — only approved agents reach the logic below.
        agent_profile = get_object_or_404(AgentProfile, user=user, is_approved=True)

        errors = {}
        phone = request.data.get('phone')
        address = request.data.get('address')
        user_fields_to_save = []

        if phone is not None:
            phone = phone.strip()
            if len(phone) > 20:
                errors['phone'] = 'Phone number must be 20 characters or fewer.'
            else:
                user.phone = phone
                user_fields_to_save.append('phone')

        if address is not None:
            user.address = address.strip()
            user_fields_to_save.append('address')

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        if user_fields_to_save:
            user.save(update_fields=user_fields_to_save)

        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            agent_profile.profile_picture = profile_picture
            agent_profile.save(update_fields=['profile_picture'])

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)