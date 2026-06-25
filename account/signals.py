# account/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AgentProfile, AffiliateProfile


@receiver(post_save, sender=AgentProfile)
def sync_agent_role_on_approval(sender, instance, **kwargs):
    """
    When an admin approves an AgentProfile (is_approved -> True),
    promote the linked user's role. Keeps role and approval status
    from drifting out of sync regardless of where approval happens
    (Django admin, a future API endpoint, etc).
    """
    user = instance.user
    if instance.is_approved and user.role != 'agent':
        user.role = 'agent'
        user.save(update_fields=['role'])
    elif not instance.is_approved and user.role == 'agent':
        # Approval was revoked — demote back to client.
        user.role = 'client'
        user.save(update_fields=['role'])


@receiver(post_save, sender=AffiliateProfile)
def sync_affiliate_role_on_approval(sender, instance, **kwargs):
    user = instance.user
    if instance.is_approved and not user.is_affiliate:
        user.is_affiliate = True
        user.role = 'affiliate'
        user.save(update_fields=['is_affiliate', 'role'])
    elif not instance.is_approved and user.is_affiliate:
        user.is_affiliate = False
        if user.role == 'affiliate':
            user.role = 'client'
        user.save(update_fields=['is_affiliate', 'role'])