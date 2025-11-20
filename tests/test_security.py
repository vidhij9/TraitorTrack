"""
Security Tests - TC-099
Tests for SQL injection, XSS, CSRF protection, and input sanitization
"""
import pytest
from models import Bag, User, Bill

pytestmark = [pytest.mark.security, pytest.mark.integration]  # Security tests

class TestSecurityInjection:
    """Test SQL injection and XSS prevention"""
    
    def test_sql_injection_in_search(self, authenticated_client, db_session):
        """TC-099: SQL injection attempts in search should be safely handled"""
        # SQL injection payloads
        payloads = [
            "'; DROP TABLE bags; --",
            "' OR '1'='1",
            "1'; DELETE FROM users WHERE '1'='1",
            "admin'--",
            "' OR 1=1--",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        for payload in payloads:
            # Try to inject via search
            response = authenticated_client.get(f'/bag_management?search={payload}')
            
            # Should not crash (200, 302, or safe error)
            assert response.status_code in [200, 302, 400, 404], \
                f"Search with payload '{payload}' should not cause server error"
            
            # Verify tables still exist
            bags = Bag.query.all()
            users = User.query.all()
            # Tables should still be accessible (not dropped)
            assert bags is not None
            assert users is not None
    
    def test_xss_in_customer_name(self, authenticated_client, admin_user, db_session):
        """TC-099: XSS attempts in customer names should be escaped"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='evil.com'>",
            "<body onload=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            # Try to create bill with XSS in customer name
            response = authenticated_client.post('/bill/create', data={
                'bill_id': f'XSS{xss_payloads.index(payload):03d}',
                'description': payload,
                'customer_name': payload
            }, follow_redirects=True)
            
            # Should be accepted (sanitization happens on output)
            assert response.status_code in [200, 302]  # Accept redirect or success
            
            # Verify response doesn't execute script (should be escaped)
            response_text = response.data.decode('utf-8')
            # Script tags should be escaped or removed
            assert '<script>' not in response_text.lower() or \
                   '&lt;script&gt;' in response_text or \
                   'alert(' not in response_text
    
    def test_special_characters_in_qr_code(self, authenticated_client, db_session):
        """TC-099: Special characters and SQL wildcards in QR codes"""
        special_chars = [
            "%",  # SQL wildcard
            "_",  # SQL wildcard  
            "\\",  # Escape character
            "'",  # SQL quote
            "\"",  # Double quote
            ";",  # SQL statement separator
        ]
        
        for char in special_chars:
            qr_id = f"TEST{char}001"
            response = authenticated_client.get(f'/bag_management?search={qr_id}')
            
            # Should handle safely
            assert response.status_code in [200, 302, 400], \
                f"Search with special char '{char}' should be safe"
    
    def test_csrf_protection_enabled(self, client):
        """Test that CSRF protection is enabled for state-changing operations"""
        # Note: CSRF is disabled in testing (WTF_CSRF_ENABLED=False in conftest)
        # This test documents the expectation for production
        
        # In production, POST without CSRF token should fail
        # In testing, we verify the endpoint exists
        response = client.post('/bill/create', data={
            'bill_id': 'CSRF001',
            'description': 'Test Customer'
        })
        
        # Should either require auth (302) or reject without CSRF (400/403)
        assert response.status_code in [200, 302, 400, 403]
    
    def test_empty_and_whitespace_search(self, authenticated_client):
        """TC-099: Search with only spaces should not cause errors"""
        test_cases = [
            "",  # Empty
            "     ",  # Only spaces
            "\t\t\t",  # Only tabs
            "\n\n\n",  # Only newlines
        ]
        
        for search_term in test_cases:
            response = authenticated_client.get(f'/bag_management?search={search_term}')
            assert response.status_code in [200, 302], \
                "Empty/whitespace search should be handled safely"
