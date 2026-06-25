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
        # First entry in the list is the original client.
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

        # Referral tracking — optional `referral_code` in the request body.
        # Only approved affiliates can earn credit; an invalid/unapproved
        # code is ignored silently rather than failing registration, since
        # a bad referral link shouldn't block someone from signing up.
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
                # Invalid UUID format or no matching approved affiliate —
                # don't block registration over a bad/expired referral link.
                pass

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': message,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    User login endpoint
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
    User logout endpoint (blacklist refresh token)
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
    """
    Get/Update current user profile.

    NOTE: once serializers.py exists, make sure UserSerializer marks
    `role`, `is_verified`, `is_affiliate`, `bvn`, and `nin` as read-only
    (or excludes them) for this endpoint. Otherwise a user can PATCH
    their own profile and self-promote to agent/self-verify.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        # NOTE: agent_profile.is_approved defaults to False — user.role stays
        # 'client' until an admin approves it (see account/signals.py).

        return Response({
            'message': 'Agent application submitted successfully! Please wait for admin approval.',
            'agent_profile': AgentProfileSerializer(agent_profile).data
        }, status=status.HTTP_201_CREATED)


class ApplyAffiliateView(APIView):
    """
    Apply to become an affiliate
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
        # NOTE: is_approved defaults to False — user.role/is_affiliate stay
        # unchanged until an admin approves it (see account/signals.py).

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
    Get list of all approved agents (public)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        agents = AgentProfile.objects.filter(is_approved=True)
        serializer = AgentProfileSerializer(agents, many=True)
        return Response(serializer.data)