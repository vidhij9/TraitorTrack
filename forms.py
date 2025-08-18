from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp, Optional
from models import User

class LoginForm(FlaskForm):
    """User login form with validation."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

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
    """Form for employees to request admin promotion."""
    reason = TextAreaField('Reason for Promotion Request', validators=[
        DataRequired(),
        Length(min=10, max=500, message="Reason must be between 10 and 500 characters.")
    ])
    submit = SubmitField('Submit Promotion Request')

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
    """Form to create a new bill."""
    bill_id = StringField('Bill ID', validators=[
        DataRequired(),
        Length(min=3, max=50, message="Bill ID must be between 3 and 50 characters.")
    ])
    description = StringField('Description', validators=[
        Length(max=200, message="Description must be 200 characters or less.")
    ])
    submit = SubmitField('Create Bill')
    
    def validate_bill_id(self, bill_id):
        """Check if a bill with this ID already exists."""
        from models import Bill
        existing_bill = Bill.query.filter_by(bill_id=bill_id.data).first()
        if existing_bill:
            raise ValidationError('A bill with this ID already exists. Please use a different ID.')

class ChildLookupForm(FlaskForm):
    """Form to look up child bag information."""
    qr_id = StringField('Child Bag QR Code', validators=[DataRequired()])
    submit = SubmitField('Lookup')

class ManualScanForm(FlaskForm):
    """Form for manual QR code entry during scanning."""
    qr_code = StringField('QR Code', validators=[DataRequired()])
    submit = SubmitField('Add Child')

