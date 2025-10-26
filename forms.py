from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp, Optional
from models import User
from validation_utils import InputValidator

class LoginForm(FlaskForm):
    """User login form with enhanced validation."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=20, message="Username must be between 3 and 20 characters.")
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')
    
    def validate_username(self, username):
        """Sanitize username input."""
        is_valid, error_msg = InputValidator.validate_username(username.data)
        if not is_valid:
            raise ValidationError(error_msg)

class RegistrationForm(FlaskForm):
    """User registration form with validation."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=20, message="Username must be between 3 and 20 characters."),
        Regexp('^[A-Za-z0-9_]+$', message="Username can only contain letters, numbers, and underscores.")
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long."),
        # Can add more complex validation based on requirements
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        """Check if username already exists."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        """Check if email already exists."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different one or login.')

class PromotionRequestForm(FlaskForm):
    """Form for employees to request admin promotion with enhanced validation."""
    reason = TextAreaField('Reason for Promotion Request', validators=[
        DataRequired(),
        Length(min=10, max=500, message="Reason must be between 10 and 500 characters.")
    ])
    submit = SubmitField('Submit Promotion Request')
    
    def validate_reason(self, reason):
        """Sanitize reason text to prevent XSS."""
        if reason.data:
            sanitized = InputValidator.sanitize_html(reason.data, max_length=500)
            reason.data = sanitized.strip()

class AdminPromotionForm(FlaskForm):
    """Form for admins to promote users directly."""
    user_id = SelectField('User to Promote', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Admin Notes', validators=[
        Length(max=300, message="Notes must be 300 characters or less.")
    ])
    submit = SubmitField('Promote to Admin')

class PromotionRequestActionForm(FlaskForm):
    """Form for admins to approve/reject promotion requests."""
    action = SelectField('Action', choices=[('approve', 'Approve'), ('reject', 'Reject')], validators=[DataRequired()])
    admin_notes = TextAreaField('Admin Notes', validators=[
        Length(max=300, message="Notes must be 300 characters or less.")
    ])
    submit = SubmitField('Process Request')



class BillCreationForm(FlaskForm):
    """Form to create a new bill with enhanced validation."""
    bill_id = StringField('Bill ID', validators=[
        DataRequired(),
        Length(min=3, max=50, message="Bill ID must be between 3 and 50 characters.")
    ])
    description = StringField('Description', validators=[
        Length(max=200, message="Description must be 200 characters or less.")
    ])
    submit = SubmitField('Create Bill')
    
    def validate_bill_id(self, bill_id):
        """Check if a bill with this ID already exists and sanitize."""
        # Sanitize HTML to prevent XSS
        sanitized = InputValidator.sanitize_html(bill_id.data, max_length=50)
        bill_id.data = sanitized.strip()
        
        # Check uniqueness
        from models import Bill
        existing_bill = Bill.query.filter_by(bill_id=bill_id.data).first()
        if existing_bill:
            raise ValidationError('A bill with this ID already exists. Please use a different ID.')
    
    def validate_description(self, description):
        """Sanitize description to prevent XSS."""
        if description.data:
            sanitized = InputValidator.sanitize_html(description.data, max_length=200)
            description.data = sanitized.strip()

class ChildLookupForm(FlaskForm):
    """Form to look up child bag information with QR validation."""
    qr_id = StringField('Child Bag QR Code', validators=[
        DataRequired(),
        Length(min=4, max=100, message="QR code must be between 4 and 100 characters.")
    ])
    submit = SubmitField('Lookup')
    
    def validate_qr_id(self, qr_id):
        """Validate QR code format and characters."""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code(qr_id.data)
        if not is_valid:
            raise ValidationError(error_msg)
        # Update with cleaned/normalized QR code
        qr_id.data = cleaned_qr

class ManualScanForm(FlaskForm):
    """Form for manual QR code entry during scanning with QR validation."""
    qr_code = StringField('QR Code', validators=[
        DataRequired(),
        Length(min=4, max=100, message="QR code must be between 4 and 100 characters.")
    ])
    submit = SubmitField('Add Child')
    
    def validate_qr_code(self, qr_code):
        """Validate QR code format and characters."""
        is_valid, cleaned_qr, error_msg = InputValidator.validate_qr_code(qr_code.data)
        if not is_valid:
            raise ValidationError(error_msg)
        # Update with cleaned/normalized QR code
        qr_code.data = cleaned_qr

class ForgotPasswordForm(FlaskForm):
    """Form for requesting a password reset."""
    email = StringField('Email Address', validators=[
        DataRequired(),
        Email(message="Please enter a valid email address.")
    ])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    """Form for resetting password with a token."""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Reset Password')

