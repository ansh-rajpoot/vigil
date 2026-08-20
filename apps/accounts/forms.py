from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import User, EmergencyContact


class TouristRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name', 'autocomplete': 'given-name'})
    )
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name', 'autocomplete': 'family-name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email Address (e.g. you@example.com)', 'autocomplete': 'email'})
    )
    phone_number = forms.CharField(
        max_length=20, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210', 'autocomplete': 'tel'})
    )

    # Tourist Travel Profile Details
    nationality = forms.CharField(
        max_length=50, initial='Indian', required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Indian, German, British'})
    )
    blood_group = forms.ChoiceField(
        choices=[
            ('', 'Select Blood Group (Optional)'),
            ('A+', 'A+'), ('A-', 'A-'),
            ('B+', 'B+'), ('B-', 'B-'),
            ('O+', 'O+'), ('O-', 'O-'),
            ('AB+', 'AB+'), ('AB-', 'AB-')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    hotel_stay_details = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Hotel / Resort Name & Area'})
    )

    # Primary Emergency Contact
    emergency_contact_name = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Contact Name'})
    )
    emergency_contact_phone = forms.CharField(
        max_length=20, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 00000'})
    )
    emergency_contact_relation = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Relationship (e.g. Spouse, Parent)'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Choose a unique username'})
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Create strong password'})
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Confirm password'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email


class AuthorityRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Officer First Name'})
    )
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Officer Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Official Email Address (@gov.in / @police.gov.in)'})
    )
    phone_number = forms.CharField(
        max_length=20, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Official Mobile Number'})
    )
    role = forms.ChoiceField(
        choices=[
            ('OPERATOR', 'Command & Control (C2) Operator'),
            ('AUTHORITY', 'Law Enforcement / Tourism Police Officer'),
            ('RESPONDER', '108 EMS / Emergency Field Responder'),
            ('ADMIN', 'Tourism Department Administrator')
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    agency_name = forms.CharField(
        max_length=150, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Goa Police, Tourism Task Force, 108 GVK-EMRI'})
    )
    badge_number = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Official Badge / Service Number (e.g. GOA-POL-4491)'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'agency_name', 'badge_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Official Username / Service ID'})
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Official password'})
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Confirm password'})


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username or email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password'
        })
    )


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input'}),
        }


class EmergencyContactForm(forms.ModelForm):
    class Meta:
        model = EmergencyContact
        fields = ('name', 'relationship', 'phone_number', 'email', 'is_primary')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Full Name'}),
            'relationship': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Spouse, Parent, Sister'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'optional@example.com'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
