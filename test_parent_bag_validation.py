"""
Comprehensive Unit Tests for Parent Bag Validation
Tests the new QR_PARENT_PATTERN supporting both SB##### and M444-##### formats
"""

import pytest
from validation_utils import InputValidator


class TestParentBagValidation:
    """Test suite for parent bag QR code validation"""
    
    # ==================== VALID FORMATS ====================
    
    def test_valid_mustard_format_sb12345(self):
        """Test valid mustard bag format SB12345"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB12345', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB12345'
        assert error_msg == 'Valid QR code'
    
    def test_valid_mustard_format_sb00001(self):
        """Test valid mustard bag format SB00001"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB00001', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB00001'
    
    def test_valid_mustard_format_sb99999(self):
        """Test valid mustard bag format SB99999"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB99999', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB99999'
    
    def test_invalid_mustard_format_6_digits(self):
        """Test invalid mustard bag format with 6 digits SB123456 (should fail - exactly 5 required)"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB123456', bag_type='parent')
        assert is_valid is False
        assert 'SB#####' in error_msg or 'M444-#####' in error_msg
    
    def test_valid_moong_format_m444_12345(self):
        """Test valid moong bag format M444-12345"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-12345', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'M444-12345'
        assert error_msg == 'Valid QR code'
    
    def test_valid_moong_format_m444_00001(self):
        """Test valid moong bag format M444-00001"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-00001', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'M444-00001'
    
    def test_valid_moong_format_m444_99999(self):
        """Test valid moong bag format M444-99999"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-99999', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'M444-99999'
    
    def test_invalid_moong_format_6_digits(self):
        """Test invalid moong bag format with 6 digits M444-123456 (should fail - exactly 5 required)"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-123456', bag_type='parent')
        assert is_valid is False
        assert 'SB#####' in error_msg or 'M444-#####' in error_msg
    
    # ==================== CASE NORMALIZATION ====================
    
    def test_lowercase_mustard_normalized(self):
        """Test lowercase mustard bag is normalized to uppercase"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('sb12345', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB12345'
    
    def test_mixed_case_mustard_normalized(self):
        """Test mixed case mustard bag is normalized"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('Sb12345', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB12345'
    
    def test_lowercase_moong_normalized(self):
        """Test lowercase moong bag is normalized to uppercase"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('m444-12345', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'M444-12345'
    
    def test_mixed_case_moong_normalized(self):
        """Test mixed case moong bag is normalized"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-12345', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'M444-12345'
    
    # ==================== WHITESPACE HANDLING ====================
    
    def test_leading_whitespace_removed(self):
        """Test leading whitespace is removed"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('  SB12345', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB12345'
    
    def test_trailing_whitespace_removed(self):
        """Test trailing whitespace is removed"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB12345  ', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB12345'
    
    def test_moong_whitespace_removed(self):
        """Test whitespace is removed from moong format"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('  M444-12345  ', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'M444-12345'
    
    # ==================== INVALID FORMATS ====================
    
    def test_invalid_too_few_digits_sb1234(self):
        """Test invalid mustard bag with only 4 digits"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB1234', bag_type='parent')
        assert is_valid is False
        assert 'SB#####' in error_msg or 'M444-#####' in error_msg
    
    def test_invalid_moong_too_few_digits(self):
        """Test invalid moong bag with only 4 digits"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-1234', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_wrong_prefix_mb12345(self):
        """Test invalid bag with wrong prefix MB"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('MB12345', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_wrong_prefix_m445(self):
        """Test invalid moong bag with wrong number M445"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M445-12345', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_missing_dash_m44412345(self):
        """Test invalid moong bag missing dash"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M44412345', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_extra_dash_sb_12345(self):
        """Test invalid mustard bag with dash SB-12345"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB-12345', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_letters_in_number_sb1234a(self):
        """Test invalid bag with letters in number part"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB1234A', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_special_chars_sb12345_exclaim(self):
        """Test invalid bag with special characters"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB12345!', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_empty_string(self):
        """Test invalid empty string"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('', bag_type='parent')
        assert is_valid is False
        assert 'cannot be empty' in error_msg.lower()
    
    def test_invalid_only_whitespace(self):
        """Test invalid whitespace-only string"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('   ', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_just_sb(self):
        """Test invalid QR with just 'SB'"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB', bag_type='parent')
        assert is_valid is False
    
    def test_invalid_just_m444(self):
        """Test invalid QR with just 'M444-'"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-', bag_type='parent')
        assert is_valid is False
    
    # ==================== SECURITY TESTS ====================
    
    def test_sql_injection_prevention_single_quote(self):
        """Test SQL injection with single quote is rejected"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code("SB12345'; DROP TABLE bag; --", bag_type='parent')
        assert is_valid is False
    
    def test_sql_injection_prevention_double_dash(self):
        """Test SQL injection with double dash is rejected"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code("SB12345--", bag_type='parent')
        assert is_valid is False
    
    def test_xss_prevention_script_tag(self):
        """Test XSS with script tag is rejected"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code("<script>alert('xss')</script>", bag_type='parent')
        assert is_valid is False
    
    def test_xss_prevention_html_entities(self):
        """Test XSS with HTML entities is rejected"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code("SB12345&lt;&gt;", bag_type='parent')
        assert is_valid is False
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack is rejected"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code("../../etc/passwd", bag_type='parent')
        assert is_valid is False
    
    # ==================== EDGE CASES ====================
    
    def test_very_long_digit_sequence_sb(self):
        """Test very long digit sequence for SB format (should fail - exactly 5 required)"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB12345678901234567890', bag_type='parent')
        assert is_valid is False  # Should be invalid (exactly 5 digits required)
    
    def test_very_long_digit_sequence_moong(self):
        """Test very long digit sequence for moong format (should fail - exactly 5 required)"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-12345678901234567890', bag_type='parent')
        assert is_valid is False  # Should be invalid (exactly 5 digits required)
    
    def test_max_length_exceeded(self):
        """Test QR code exceeding max length (100 chars)"""
        long_qr = 'SB' + '1' * 200
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code(long_qr, bag_type='parent')
        assert is_valid is False
        assert 'too long' in error_msg.lower()
    
    # ==================== NO BAG TYPE SPECIFIED ====================
    
    def test_no_bag_type_valid_mustard(self):
        """Test validation without bag_type specified for mustard"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB12345')
        assert is_valid is True
        assert cleaned_qr == 'SB12345'
    
    def test_no_bag_type_valid_moong(self):
        """Test validation without bag_type specified for moong"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('M444-12345')
        assert is_valid is True
        assert cleaned_qr == 'M444-12345'
    
    # ==================== REGRESSION TESTS ====================
    
    def test_regression_sb00860(self):
        """Regression test for SB00860 (known working QR)"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB00860', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB00860'
    
    def test_regression_sb00736(self):
        """Regression test for SB00736 (known working QR)"""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code('SB00736', bag_type='parent')
        assert is_valid is True
        assert cleaned_qr == 'SB00736'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
