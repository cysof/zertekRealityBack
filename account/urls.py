# account/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, UserProfileView,
    ApplyAgentView, ApplyAffiliateView, AgentProfileView,
    AffiliateProfileView, AgentListView, AgentSocialProfileUpdateView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('agent-profile/', AgentSocialProfileUpdateView.as_view(), name='agent-profile-update'),  # ← new
    path('apply/agent/', ApplyAgentView.as_view(), name='apply-agent'),
    path('apply/affiliate/', ApplyAffiliateView.as_view(), name='apply-affiliate'),
    path('agents/', AgentListView.as_view(), name='agent-list'),
    path('agents/<int:user_id>/', AgentProfileView.as_view(), name='agent-profile'),
    path('affiliates/<int:user_id>/', AffiliateProfileView.as_view(), name='affiliate-profile'),
]