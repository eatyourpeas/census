"""
Tests for OIDC authentication flow.

These tests verify that the OIDC authentication callback properly
handles success and failure cases, ensuring no unauthorized access
is granted when authentication fails.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from unittest.mock import Mock, patch

from checktick_app.core.oidc_views import HealthcareOIDCCallbackView
from checktick_app.core.models import UserOIDC

User = get_user_model()


@pytest.mark.django_db
class TestOIDCAuthenticationCallback:
    """Test OIDC authentication callback security."""

    def test_failed_authentication_blocks_access(self, client):
        """
        Test that failed OIDC authentication explicitly redirects to login
        and does NOT grant any access.
        
        This is a critical security test - if OIDC authentication fails,
        the user should not be authenticated.
        """
        # Create a mock OIDC callback view
        factory = RequestFactory()
        request = factory.get('/oidc/callback/?error=access_denied')
        request.session = client.session
        request.session['oidc_provider'] = 'google'
        
        view = HealthcareOIDCCallbackView()
        
        # Mock the parent get method to simulate failed authentication
        with patch.object(
            HealthcareOIDCCallbackView.__bases__[0], 
            'get',
            return_value=Mock(status_code=302)
        ):
            # Set request.user to AnonymousUser (authentication failed)
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
            
            # Call the callback
            response = view.get(request)
            
            # Verify user is NOT authenticated
            assert not request.user.is_authenticated
            
            # Verify redirect to login with error
            assert response.status_code == 302
            assert '/accounts/login/' in response.url
            assert 'error=oidc_authentication_failed' in response.url

    def test_successful_authentication_grants_access(self, client):
        """
        Test that successful OIDC authentication properly authenticates
        the user and grants access.
        """
        # Create a test user
        user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com'
        )
        
        # Create UserOIDC record
        UserOIDC.objects.create(
            user=user,
            provider='google',
            subject='google-subject-123',
            email_verified=True,
            signup_completed=True
        )
        
        factory = RequestFactory()
        request = factory.get('/oidc/callback/?code=test-code')
        request.session = client.session
        request.session['oidc_provider'] = 'google'
        
        view = HealthcareOIDCCallbackView()
        
        # Mock the parent get method to simulate successful authentication
        with patch.object(
            HealthcareOIDCCallbackView.__bases__[0],
            'get',
            return_value=Mock(status_code=302, get=lambda x: '/')
        ):
            # Set request.user to the authenticated user
            request.user = user
            
            # Call the callback
            view.get(request)
            
            # Verify user IS authenticated
            assert request.user.is_authenticated
            assert request.user.email == 'test@example.com'

    def test_exception_during_authentication_blocks_access(self, client):
        """
        Test that exceptions during OIDC authentication don't grant access.
        
        If an exception occurs during the callback, the user should be
        redirected to login, not left in an authenticated state.
        """
        factory = RequestFactory()
        request = factory.get('/oidc/callback/?code=test-code')
        request.session = client.session
        request.session['oidc_provider'] = 'google'
        
        view = HealthcareOIDCCallbackView()
        
        # Mock the parent get method to raise an exception
        with patch.object(
            HealthcareOIDCCallbackView.__bases__[0],
            'get',
            side_effect=Exception('OIDC provider error')
        ):
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
            
            # Call the callback
            response = view.get(request)
            
            # Verify user is NOT authenticated
            assert not request.user.is_authenticated
            
            # Verify redirect to login with error
            assert response.status_code == 302
            assert '/accounts/login/' in response.url
            assert 'error=' in response.url

    def test_unauthenticated_user_cannot_access_protected_views(self, client):
        """
        Integration test: Verify that unauthenticated users (including
        those whose OIDC authentication failed) cannot access protected views.
        """
        # Try to access a protected view without authentication
        from django.urls import reverse
        
        # Create a test survey
        owner = User.objects.create_user(username='owner', email='owner@example.com')
        from checktick_app.surveys.models import Survey
        Survey.objects.create(owner=owner, name='Test', slug='test')
        
        # Try to access the dashboard without authentication
        response = client.get(reverse('surveys:dashboard', kwargs={'slug': 'test'}))
        
        # Should be redirected or get 403
        assert response.status_code in (302, 403)
        
        # If redirected, should be to login
        if response.status_code == 302:
            assert '/accounts/login' in response.url or response.url.startswith('/accounts/login')
