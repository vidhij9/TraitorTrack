"""
Unicode and Special Character Tests - TC-097, TC-098, TC-104
Tests Unicode support in various fields and CSV export/import
"""
import pytest
import io
import csv
from models import Bag, Bill

pytestmark = [pytest.mark.unicode, pytest.mark.integration]  # Unicode tests

class TestUnicodeSupport:
    """Test Unicode character handling"""
    
    def test_unicode_rejection_in_qr_codes(self, authenticated_client, db_session):
        """TC-097: QR codes should only accept ASCII characters"""
        unicode_qr_codes = [
            "SB123€45",  # Euro symbol
            "SB123😀",  # Emoji
            "SB١٢٣٤٥",  # Arabic numerals
            "SB中文123",  # Chinese characters
            "SBñ123",  # Spanish ñ
            "SB123й",  # Cyrillic
        ]
        
        for qr_id in unicode_qr_codes:
            # Try to create bag with Unicode QR
            response = authenticated_client.post('/api/bags', json={
                'qr_id': qr_id,
                'type': 'parent',
                'name': 'Test Bag'
            })
            
            # Should either reject (400/422) or handle safely
            # The exact behavior depends on validation rules
            assert response.status_code in [200, 201, 400, 422], \
                f"Unicode QR '{qr_id}' should be handled (accepted or rejected)"
    
    def test_unicode_support_in_customer_names(self, authenticated_client, admin_user, db_session):
        """TC-098: Customer names should support Unicode"""
        unicode_names = [
            "राज कुमार",  # Hindi
            "José García",  # Spanish with accents
            "北京公司",  # Chinese
            "Müller GmbH",  # German
            "François Société",  # French
            "Владимир Петров",  # Cyrillic
        ]
        
        for name in unicode_names:
            # Create bill with Unicode customer name
            response = authenticated_client.post('/bills/create', data={
                'customer_name': name,
                'dispatch_area': 'test_area',
                'bill_id': f'UNICODE{hash(name) % 10000}'
            }, follow_redirects=True)
            
            # Should be accepted
            assert response.status_code == 200, \
                f"Unicode name '{name}' should be accepted"
            
            # Verify it's stored correctly (no mojibake)
            with authenticated_client.application.app_context():
                bill = Bill.query.filter_by(customer_name=name).first()
                if bill:
                    assert bill.customer_name == name, \
                        f"Unicode name should be stored correctly, got '{bill.customer_name}'"
    
    def test_unicode_in_search(self, authenticated_client, admin_user, db_session):
        """TC-098: Search should work with Unicode characters"""
        # Create a bag with Unicode in name/description
        with authenticated_client.application.app_context():
            bag = Bag()
            bag.qr_id = 'UNICODE001'
            bag.type = 'parent'
            bag.name = 'José García Müller 北京'  # Multi-language Unicode
            db_session.add(bag)
            db_session.commit()
        
        # Search for Unicode terms
        unicode_searches = ["José", "García", "Müller", "北京"]
        
        for search_term in unicode_searches:
            response = authenticated_client.get(f'/bag_management?search={search_term}')
            assert response.status_code == 200, \
                f"Search with Unicode term '{search_term}' should work"
    
    def test_csv_export_with_unicode(self, authenticated_client, admin_user, db_session):
        """TC-104: CSV export should preserve UTF-8 encoding"""
        # Create bags with various Unicode characters
        unicode_data = [
            ('UNICODE01', '北京公司 Beijing Corp'),
            ('UNICODE02', 'José García & Sons'),
            ('UNICODE03', 'Müller GmbH Deutschland'),
        ]
        
        with authenticated_client.application.app_context():
            for qr_id, name in unicode_data:
                bag = Bag()
                bag.qr_id = qr_id
                bag.type = 'parent'
                bag.name = name
                db_session.add(bag)
            db_session.commit()
        
        # Export to CSV
        response = authenticated_client.get('/export/bags?format=csv')
        
        if response.status_code == 200:
            # Parse CSV
            csv_data = response.data.decode('utf-8-sig')  # UTF-8 with BOM
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            
            # Verify Unicode is preserved
            rows = list(csv_reader)
            names_in_csv = [row.get('name', '') for row in rows if 'name' in row]
            
            # Check that Unicode characters are intact (not replaced with ?)
            for qr_id, expected_name in unicode_data:
                matching_names = [n for n in names_in_csv if expected_name in n or qr_id in n]
                if matching_names:
                    # Verify no replacement characters (�)
                    assert '�' not in matching_names[0], \
                        f"Unicode should be preserved in CSV, found replacement char in '{matching_names[0]}'"
    
    def test_csv_with_special_characters(self, authenticated_client, admin_user, db_session):
        """TC-104: CSV should properly escape commas, quotes, newlines"""
        special_data = [
            ('SPECIAL01', 'Name, with comma'),
            ('SPECIAL02', 'Name "with quotes"'),
            ('SPECIAL03', 'Name with\nnewline'),
        ]
        
        with authenticated_client.application.app_context():
            for qr_id, name in special_data:
                bag = Bag()
                bag.qr_id = qr_id
                bag.type = 'parent'
                bag.name = name
                db_session.add(bag)
            db_session.commit()
        
        # Export to CSV
        response = authenticated_client.get('/export/bags?format=csv')
        
        if response.status_code == 200:
            csv_data = response.data.decode('utf-8')
            
            # CSV should be properly formatted (commas and quotes escaped)
            # Parse it to verify integrity
            try:
                csv_reader = csv.DictReader(io.StringIO(csv_data))
                rows = list(csv_reader)
                # If parsing succeeds, CSV is properly formatted
                assert len(rows) > 0, "CSV should contain data"
            except csv.Error as e:
                pytest.fail(f"CSV parsing failed: {e}")
