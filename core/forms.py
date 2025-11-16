# core/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.db import transaction
from users.models import User, ClientProfile

class ClientRegistrationForm(forms.ModelForm):
    # --- 1. We'll explicitly set labels here ---
    email = forms.EmailField(required=True, label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    company_name = forms.CharField(max_length=255, required=True, label="Company Name")

    class Meta:
        model = User
        fields = ('username', 'email', 'company_name', 'password', 'password2')

    # --- 2. This is the corrected __init__ method ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # We'll set placeholders manually to be safer
        placeholders = {
            'username': 'Create a username',
            'email': 'Enter your email',
            'company_name': 'Enter your company name',
            'password': 'Create a password',
            'password2': 'Confirm your password',
        }

        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control', 
                'placeholder': placeholders.get(field_name, '') # Use the placeholder
            })

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
        
    def clean_company_name(self):
        company_name = self.cleaned_data.get('company_name')
        if ClientProfile.objects.filter(company_name=company_name).exists():
            raise forms.ValidationError("A client with this company name already exists.")
        return company_name

    @transaction.atomic
    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data.get('username'),
            email=self.cleaned_data.get('email'),
            password=self.cleaned_data.get('password'),
            role=User.Role.CLIENT
        )
        ClientProfile.objects.create(
            user=user,
            company_name=self.cleaned_data.get('company_name')
        )
        return user
    
class ClientProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    company_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your contact number'})
    )
    # ✅ Keep theme here, but NOT in Meta
    theme = forms.ChoiceField(
        choices=[('light', 'Light'), ('dark', 'Dark')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = ClientProfile
        fields = ['company_name', 'phone_number']  # ❌ Removed 'theme'

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
            self.fields['theme'].initial = getattr(self.user, 'theme', 'light')

    def clean_email(self):
        # ✅ Avoid validation error when email is read-only
        email = self.cleaned_data.get('email', self.user.email)
        if self.user and User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This email address is already in use by another account.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = self.user

        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.last_name = self.cleaned_data.get('last_name', user.last_name)
        user.email = self.cleaned_data.get('email', user.email)
        user.theme = self.cleaned_data.get('theme', user.theme)

        if commit:
            user.save()
            profile.save()

        return profile


# --- NEW: CLIENT PASSWORD CHANGE FORM ---
class ClientPasswordChangeForm(PasswordChangeForm):
    # We override the fields to add Bootstrap classes
    old_password = forms.CharField(
        label="Old Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'})
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'})
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'})
    )