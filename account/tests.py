# # account/tests.py
# from django.test import TestCase
# from django.contrib.auth import get_user_model
# from rest_framework.test import APIClient
# from rest_framework import status
# from django.urls import reverse
# from unittest.mock import patch
# from .models import AgentProfile, AffiliateProfile, Referral
#
# User = get_user_model()
#
#
# class AccountTests(TestCase):
#     """
#     Test suite for account app (User, AgentProfile, AffiliateProfile, Referral)
#     """
#
#     def setUp(self):
#         self.client = APIClient()
#
#         # Test user data
#         self.user_data = {
#             'email': 'testuser@example.com',
#             'first_name': 'Test',
#             'last_name': 'User',
#             'phone': '+2348012345678',
#             'password': 'SecurePass123!',
#             'password2': 'SecurePass123!',
#         }
#
#         self.agent_data = {
#             'email': 'agent@example.com',
#             'first_name': 'Agent',
#             'last_name': 'User',
#             'phone': '+2348023456789',
#             'password': 'SecurePass123!',
#             'password2': 'SecurePass123!',
#         }
#
#         self.affiliate_data = {
#             'email': 'affiliate@example.com',
#             'first_name': 'Affiliate',
#             'last_name': 'User',
#             'phone': '+2348034567890',
#             'password': 'SecurePass123!',
#             'password2': 'SecurePass123!',
#         }
#
#         # Registration URLs
#         self.register_url = reverse('register')
#         self.login_url = reverse('login')
#         self.logout_url = reverse('logout')
#         self.profile_url = reverse('profile')
#         self.token_refresh_url = reverse('token-refresh')
#         self.apply_agent_url = reverse('apply-agent')
#         self.apply_affiliate_url = reverse('apply-affiliate')
#
#
# class UserRegistrationTests(AccountTests):
#     """Test user registration"""
#
#     def test_register_client_success(self):
#         """Test successful registration as client"""
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertIn('access', response.data)
#         self.assertIn('refresh', response.data)
#         self.assertEqual(response.data['user']['email'], self.user_data['email'])
#         self.assertEqual(response.data['user']['role'], 'client')
#         self.assertEqual(response.data['message'], 'Registration successful!')
#
#         # Verify user was created
#         user = User.objects.get(email=self.user_data['email'])
#         self.assertEqual(user.role, 'client')
#         self.assertFalse(user.is_verified)
#         self.assertFalse(user.is_affiliate)
#
#     def test_register_agent_success(self):
#         """Test successful registration as agent (pending approval)"""
#         data = self.agent_data.copy()
#         data['requested_role'] = 'agent'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(response.data['user']['role'], 'client')  # Still client until approved
#
#         # Verify agent profile was created
#         user = User.objects.get(email=self.agent_data['email'])
#         self.assertTrue(hasattr(user, 'agent_profile'))
#         self.assertFalse(user.agent_profile.is_approved)
#         self.assertEqual(
#             response.data['message'],
#             'Registration successful! Your agent application has been submitted and is awaiting admin approval.'
#         )
#
#     def test_register_affiliate_success(self):
#         """Test successful registration as affiliate (pending approval)"""
#         data = self.affiliate_data.copy()
#         data['requested_role'] = 'affiliate'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(response.data['user']['role'], 'client')
#         self.assertFalse(response.data['user']['is_affiliate'])
#
#         # Verify affiliate profile was created
#         user = User.objects.get(email=self.affiliate_data['email'])
#         self.assertTrue(hasattr(user, 'affiliate_profile'))
#         self.assertFalse(user.affiliate_profile.is_approved)
#         self.assertEqual(
#             response.data['message'],
#             'Registration successful! Your affiliate application has been submitted and is awaiting admin approval.'
#         )
#
#     def test_register_password_mismatch(self):
#         """Test registration with mismatched passwords"""
#         data = self.user_data.copy()
#         data['password2'] = 'DifferentPass123!'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('password', response.data)
#
#     def test_register_duplicate_email(self):
#         """Test registration with duplicate email"""
#         # Create first user
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         self.client.post(self.register_url, data)
#
#         # Try to create same user again
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('email', response.data)
#
#     def test_register_invalid_bvn(self):
#         """Test registration with invalid BVN format"""
#         data = self.user_data.copy()
#         data['bvn'] = '123456789'  # Only 9 digits, should be 11
#         data['requested_role'] = 'client'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('bvn', response.data)
#
#     def test_register_invalid_nin(self):
#         """Test registration with invalid NIN format"""
#         data = self.user_data.copy()
#         data['nin'] = '123456789'  # Only 9 digits, should be 11
#         data['requested_role'] = 'client'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('nin', response.data)
#
#
# class UserLoginTests(AccountTests):
#     """Test user login"""
#
#     def setUp(self):
#         super().setUp()
#         # Create a user
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         self.client.post(self.register_url, data)
#
#     def test_login_success(self):
#         """Test successful login"""
#         response = self.client.post(self.login_url, {
#             'email': self.user_data['email'],
#             'password': self.user_data['password']
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn('access', response.data)
#         self.assertIn('refresh', response.data)
#         self.assertEqual(response.data['user']['email'], self.user_data['email'])
#
#     def test_login_invalid_password(self):
#         """Test login with invalid password"""
#         response = self.client.post(self.login_url, {
#             'email': self.user_data['email'],
#             'password': 'WrongPass123!'
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
#         self.assertEqual(response.data['error'], 'Invalid credentials')
#
#     def test_login_missing_credentials(self):
#         """Test login with missing credentials"""
#         response = self.client.post(self.login_url, {
#             'email': self.user_data['email']
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertEqual(response.data['error'], 'Email and password are required')
#
#
# class UserProfileTests(AccountTests):
#     """Test user profile endpoints"""
#
#     def setUp(self):
#         super().setUp()
#         # Create and login user
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         self.client.post(self.register_url, data)
#
#         login_response = self.client.post(self.login_url, {
#             'email': self.user_data['email'],
#             'password': self.user_data['password']
#         })
#         self.access_token = login_response.data['access']
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
#
#     def test_get_profile_success(self):
#         """Test getting user profile"""
#         response = self.client.get(self.profile_url)
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['email'], self.user_data['email'])
#         self.assertEqual(response.data['first_name'], self.user_data['first_name'])
#
#     def test_patch_profile_success(self):
#         """Test updating user profile"""
#         response = self.client.patch(self.profile_url, {
#             'first_name': 'Updated',
#             'address': '123 Abuja, Nigeria'
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['first_name'], 'Updated')
#         self.assertEqual(response.data['address'], '123 Abuja, Nigeria')
#
#         # Verify database update
#         user = User.objects.get(email=self.user_data['email'])
#         self.assertEqual(user.first_name, 'Updated')
#
#     def test_patch_profile_read_only_fields(self):
#         """Test that read-only fields cannot be updated via PATCH"""
#         response = self.client.patch(self.profile_url, {
#             'role': 'agent',
#             'is_verified': True,
#             'is_affiliate': True,
#             'bvn': '12345678901'
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#         # Verify fields were NOT updated
#         user = User.objects.get(email=self.user_data['email'])
#         self.assertEqual(user.role, 'client')
#         self.assertFalse(user.is_verified)
#         self.assertFalse(user.is_affiliate)
#         self.assertIsNone(user.bvn)
#
#     def test_profile_unauthenticated(self):
#         """Test profile access without authentication"""
#         self.client.credentials()  # Remove auth
#         response = self.client.get(self.profile_url)
#
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
#
#
# class LogoutTests(AccountTests):
#     """Test logout functionality"""
#
#     def setUp(self):
#         super().setUp()
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         self.client.post(self.register_url, data)
#
#         login_response = self.client.post(self.login_url, {
#             'email': self.user_data['email'],
#             'password': self.user_data['password']
#         })
#         self.access_token = login_response.data['access']
#         self.refresh_token = login_response.data['refresh']
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
#
#     def test_logout_success(self):
#         """Test successful logout"""
#         response = self.client.post(self.logout_url, {
#             'refresh': self.refresh_token
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['message'], 'Logged out successfully')
#
#     def test_logout_invalid_token(self):
#         """Test logout with invalid refresh token"""
#         response = self.client.post(self.logout_url, {
#             'refresh': 'invalid_token'
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#
#
# class AgentApplicationTests(AccountTests):
#     """Test agent application flow"""
#
#     def setUp(self):
#         super().setUp()
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         self.client.post(self.register_url, data)
#
#         login_response = self.client.post(self.login_url, {
#             'email': self.user_data['email'],
#             'password': self.user_data['password']
#         })
#         self.access_token = login_response.data['access']
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
#
#     def test_apply_agent_success(self):
#         """Test applying to become an agent"""
#         response = self.client.post(self.apply_agent_url, {
#             'bio': 'Experienced real estate agent with 5 years in Abuja.',
#             'years_experience': 5,
#             'specialization': 'Maitama, Asokoro, Guzape',
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertIn('message', response.data)
#         self.assertEqual(
#             response.data['message'],
#             'Agent application submitted successfully! Please wait for admin approval.'
#         )
#
#         # Verify agent profile was created
#         user = User.objects.get(email=self.user_data['email'])
#         self.assertTrue(hasattr(user, 'agent_profile'))
#         self.assertEqual(user.agent_profile.years_experience, 5)
#         self.assertEqual(user.agent_profile.specialization, 'Maitama, Asokoro, Guzape')
#         self.assertFalse(user.agent_profile.is_approved)
#
#     def test_apply_agent_already_has_profile(self):
#         """Test applying when user already has an agent profile"""
#         # First application
#         self.client.post(self.apply_agent_url, {
#             'years_experience': 3
#         })
#
#         # Second application
#         response = self.client.post(self.apply_agent_url, {
#             'years_experience': 5
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertEqual(response.data['error'], 'You already have an agent profile')
#
#     def test_apply_agent_unauthenticated(self):
#         """Test applying without authentication"""
#         self.client.credentials()
#         response = self.client.post(self.apply_agent_url, {
#             'years_experience': 5
#         })
#
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
#
#
# class AffiliateApplicationTests(AccountTests):
#     """Test affiliate application flow"""
#
#     def setUp(self):
#         super().setUp()
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         self.client.post(self.register_url, data)
#
#         login_response = self.client.post(self.login_url, {
#             'email': self.user_data['email'],
#             'password': self.user_data['password']
#         })
#         self.access_token = login_response.data['access']
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
#
#     def test_apply_affiliate_success(self):
#         """Test applying to become an affiliate"""
#         response = self.client.post(self.apply_affiliate_url, {})
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(
#             response.data['message'],
#             'Affiliate application submitted successfully! Please wait for admin approval.'
#         )
#
#         # Verify affiliate profile was created
#         user = User.objects.get(email=self.user_data['email'])
#         self.assertTrue(hasattr(user, 'affiliate_profile'))
#         self.assertFalse(user.affiliate_profile.is_approved)
#
#     def test_apply_affiliate_already_has_profile(self):
#         """Test applying when user already has an affiliate profile"""
#         # First application
#         self.client.post(self.apply_affiliate_url, {})
#
#         # Second application
#         response = self.client.post(self.apply_affiliate_url, {})
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertEqual(response.data['error'], 'You already have an affiliate profile')
#
#
# class PublicProfileTests(AccountTests):
#     """Test public profile endpoints"""
#
#     def setUp(self):
#         super().setUp()
#         # Create an approved agent
#         agent_data = self.agent_data.copy()
#         agent_data['requested_role'] = 'agent'
#         self.client.post(self.register_url, agent_data)
#
#         agent_user = User.objects.get(email=self.agent_data['email'])
#         agent_profile = agent_user.agent_profile
#         agent_profile.is_approved = True
#         agent_profile.save()
#
#         # Create an approved affiliate
#         affiliate_data = self.affiliate_data.copy()
#         affiliate_data['requested_role'] = 'affiliate'
#         self.client.post(self.register_url, affiliate_data)
#
#         affiliate_user = User.objects.get(email=self.affiliate_data['email'])
#         affiliate_profile = affiliate_user.affiliate_profile
#         affiliate_profile.is_approved = True
#         affiliate_profile.save()
#
#         self.agent_user_id = agent_user.id
#         self.affiliate_user_id = affiliate_user.id
#
#         self.agent_profile_url = reverse('agent-profile', kwargs={'user_id': self.agent_user_id})
#         self.affiliate_profile_url = reverse('affiliate-profile', kwargs={'user_id': self.affiliate_user_id})
#
#     def test_get_agent_profile_success(self):
#         """Test getting approved agent profile"""
#         response = self.client.get(self.agent_profile_url)
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['user']['email'], self.agent_data['email'])
#         self.assertTrue(response.data['is_approved'])
#
#     def test_get_agent_profile_unapproved(self):
#         """Test getting unapproved agent profile returns 404"""
#         # Create unapproved agent
#         unapproved_data = {
#             'email': 'unapproved@example.com',
#             'first_name': 'Unapproved',
#             'last_name': 'Agent',
#             'phone': '+2348045678901',
#             'password': 'SecurePass123!',
#             'password2': 'SecurePass123!',
#             'requested_role': 'agent'
#         }
#         self.client.post(self.register_url, unapproved_data)
#
#         unapproved_user = User.objects.get(email='unapproved@example.com')
#         url = reverse('agent-profile', kwargs={'user_id': unapproved_user.id})
#         response = self.client.get(url)
#
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#
#     def test_get_affiliate_profile_success(self):
#         """Test getting approved affiliate profile"""
#         response = self.client.get(self.affiliate_profile_url)
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['user']['email'], self.affiliate_data['email'])
#         self.assertTrue(response.data['is_approved'])
#
#
# class AgentProfileSignalTests(AccountTests):
#     """Test agent profile signals"""
#
#     def test_agent_approval_signal_syncs_role(self):
#         """Test that approving an agent profile updates user role"""
#         # Create agent user
#         data = self.agent_data.copy()
#         data['requested_role'] = 'agent'
#         self.client.post(self.register_url, data)
#
#         user = User.objects.get(email=self.agent_data['email'])
#         self.assertEqual(user.role, 'client')
#         self.assertFalse(user.agent_profile.is_approved)
#
#         # Approve agent
#         user.agent_profile.is_approved = True
#         user.agent_profile.save()
#
#         # Refresh user from database
#         user.refresh_from_db()
#         self.assertEqual(user.role, 'agent')
#
#         # Revoke approval
#         user.agent_profile.is_approved = False
#         user.agent_profile.save()
#
#         user.refresh_from_db()
#         self.assertEqual(user.role, 'client')
#
#     def test_affiliate_approval_signal_syncs_role(self):
#         """Test that approving an affiliate profile updates user role"""
#         # Create affiliate user
#         data = self.affiliate_data.copy()
#         data['requested_role'] = 'affiliate'
#         self.client.post(self.register_url, data)
#
#         user = User.objects.get(email=self.affiliate_data['email'])
#         self.assertEqual(user.role, 'client')
#         self.assertFalse(user.is_affiliate)
#         self.assertFalse(user.affiliate_profile.is_approved)
#
#         # Approve affiliate
#         user.affiliate_profile.is_approved = True
#         user.affiliate_profile.save()
#
#         # Refresh user from database
#         user.refresh_from_db()
#         self.assertEqual(user.role, 'affiliate')
#         self.assertTrue(user.is_affiliate)
#
#         # Revoke approval
#         user.affiliate_profile.is_approved = False
#         user.affiliate_profile.save()
#
#         user.refresh_from_db()
#         self.assertEqual(user.role, 'client')
#         self.assertFalse(user.is_affiliate)
#
#
# class ReferralTests(AccountTests):
#     """Test referral tracking"""
#
#     def setUp(self):
#         super().setUp()
#         # Create approved affiliate
#         affiliate_data = self.affiliate_data.copy()
#         affiliate_data['requested_role'] = 'affiliate'
#         self.client.post(self.register_url, affiliate_data)
#
#         affiliate_user = User.objects.get(email=self.affiliate_data['email'])
#         affiliate_profile = affiliate_user.affiliate_profile
#         affiliate_profile.is_approved = True
#         affiliate_profile.save()
#
#         self.affiliate_profile = affiliate_profile
#
#     def test_referral_creation(self):
#         """Test creating a referral"""
#         # Create referred user
#         referred_user = User.objects.create(
#             email='referred@example.com',
#             first_name='Referred',
#             last_name='User',
#             phone='+2348056789012'
#         )
#
#         referral = Referral.objects.create(
#             affiliate=self.affiliate_profile,
#             referred_user=referred_user
#         )
#
#         self.assertIsNotNone(referral)
#         self.assertEqual(referral.affiliate, self.affiliate_profile)
#         self.assertEqual(referral.status, 'pending')
#
#     def test_referral_tracking_fields(self):
#         """Test referral model fields"""
#         referred_user = User.objects.create(
#             email='referred2@example.com',
#             first_name='Referred2',
#             last_name='User',
#             phone='+2348067890123'
#         )
#
#         referral = Referral.objects.create(
#             affiliate=self.affiliate_profile,
#             referred_user=referred_user,
#             ip_address='127.0.0.1',
#             user_agent='Mozilla/5.0 (Test)'
#         )
#
#         self.assertEqual(referral.ip_address, '127.0.0.1')
#         self.assertEqual(referral.user_agent, 'Mozilla/5.0 (Test)')
#         self.assertEqual(referral.status, 'pending')
#         self.assertFalse(referral.is_commission_paid)
#         self.assertEqual(referral.commission_amount, 0)
#
#
# class BVNNINUniqueTests(AccountTests):
#     """Test BVN and NIN unique constraints"""
#
#     def test_bvn_unique_constraint(self):
#         """Test that duplicate BVN is rejected"""
#         # Create first user with BVN
#         data1 = self.user_data.copy()
#         data1['email'] = 'user1@example.com'
#         data1['bvn'] = '12345678901'
#         data1['requested_role'] = 'client'
#         self.client.post(self.register_url, data1)
#
#         # Create second user with same BVN
#         data2 = self.user_data.copy()
#         data2['email'] = 'user2@example.com'
#         data2['bvn'] = '12345678901'
#         data2['requested_role'] = 'client'
#
#         response = self.client.post(self.register_url, data2)
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('bvn', response.data)
#
#     def test_nin_unique_constraint(self):
#         """Test that duplicate NIN is rejected"""
#         # Create first user with NIN
#         data1 = self.user_data.copy()
#         data1['email'] = 'user1@example.com'
#         data1['nin'] = '98765432101'
#         data1['requested_role'] = 'client'
#         self.client.post(self.register_url, data1)
#
#         # Create second user with same NIN
#         data2 = self.user_data.copy()
#         data2['email'] = 'user2@example.com'
#         data2['nin'] = '98765432101'
#         data2['requested_role'] = 'client'
#
#         response = self.client.post(self.register_url, data2)
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('nin', response.data)
#
#     def test_blank_bvn_converted_to_null(self):
#         """Test that empty string BVN is converted to None"""
#         data = self.user_data.copy()
#         data['bvn'] = ''
#         data['requested_role'] = 'client'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#
#         user = User.objects.get(email=self.user_data['email'])
#         self.assertIsNone(user.bvn)
#
#
# class ReferralRegistrationTests(AccountTests):
#     """Test referral tracking wired into registration"""
#
#     def setUp(self):
#         super().setUp()
#         # Create an approved affiliate to refer people
#         affiliate_data = self.affiliate_data.copy()
#         affiliate_data['requested_role'] = 'affiliate'
#         self.client.post(self.register_url, affiliate_data)
#
#         self.affiliate_user = User.objects.get(email=self.affiliate_data['email'])
#         self.affiliate_profile = self.affiliate_user.affiliate_profile
#         self.affiliate_profile.is_approved = True
#         self.affiliate_profile.save()
#
#     def test_register_with_valid_referral_code_creates_referral(self):
#         """Registering with an approved affiliate's referral_code creates a Referral"""
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         data['referral_code'] = str(self.affiliate_profile.referral_code)
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#
#         referred_user = User.objects.get(email=self.user_data['email'])
#         referral = Referral.objects.get(referred_user=referred_user)
#
#         self.assertEqual(referral.affiliate, self.affiliate_profile)
#         self.assertEqual(referral.status, 'pending')
#         self.assertFalse(referral.is_commission_paid)
#         self.assertEqual(referral.commission_amount, 0)
#         self.assertIsNotNone(referral.ip_address)
#
#     def test_register_with_referral_code_increments_total_referrals(self):
#         """total_referrals on the affiliate profile increments on a successful referral"""
#         self.assertEqual(self.affiliate_profile.total_referrals, 0)
#
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         data['referral_code'] = str(self.affiliate_profile.referral_code)
#
#         self.client.post(self.register_url, data)
#
#         self.affiliate_profile.refresh_from_db()
#         self.assertEqual(self.affiliate_profile.total_referrals, 1)
#
#     def test_register_with_unapproved_affiliate_referral_code_ignored(self):
#         """Referral codes belonging to an unapproved affiliate don't create a Referral"""
#         self.affiliate_profile.is_approved = False
#         self.affiliate_profile.save()
#
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         data['referral_code'] = str(self.affiliate_profile.referral_code)
#
#         response = self.client.post(self.register_url, data)
#
#         # Registration should still succeed even though the referral is dropped
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#
#         referred_user = User.objects.get(email=self.user_data['email'])
#         self.assertFalse(Referral.objects.filter(referred_user=referred_user).exists())
#
#     def test_register_with_unknown_referral_code_ignored(self):
#         """A well-formed but nonexistent referral_code doesn't block registration"""
#         import uuid
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         data['referral_code'] = str(uuid.uuid4())
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#
#         referred_user = User.objects.get(email=self.user_data['email'])
#         self.assertFalse(Referral.objects.filter(referred_user=referred_user).exists())
#
#     def test_register_with_malformed_referral_code_ignored(self):
#         """A non-UUID referral_code doesn't error out registration"""
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#         data['referral_code'] = 'not-a-valid-uuid'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#
#         referred_user = User.objects.get(email=self.user_data['email'])
#         self.assertFalse(Referral.objects.filter(referred_user=referred_user).exists())
#
#     def test_register_without_referral_code_no_referral_created(self):
#         """Normal registration (no referral_code) creates no Referral record"""
#         data = self.user_data.copy()
#         data['requested_role'] = 'client'
#
#         response = self.client.post(self.register_url, data)
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(Referral.objects.count(), 0)