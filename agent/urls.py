# agent/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PropertyViewSet,
    InquiryViewSet,
    LandBankingPlanViewSet,
    LandBankingAgreementViewSet,
    PaymentViewSet,
    PaymentReminderViewSet,
    AgentPropertyStatsView,
)

router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'land-banking-plans', LandBankingPlanViewSet, basename='land-banking-plan')
router.register(r'land-banking-agreements', LandBankingAgreementViewSet, basename='land-banking-agreement')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'payment-reminders', PaymentReminderViewSet, basename='payment-reminder')


urlpatterns = [
    path('', include(router.urls)),  # This includes the router at the root
    path('agent/stats/', AgentPropertyStatsView.as_view(), name='agent-property-stats'),
    # path('agent/profile/', AgentProfileUpdateView.as_view(), name='agent-profile-update'),
]
