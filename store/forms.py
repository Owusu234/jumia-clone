from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import SellerProfile, Product, Review, UserProfile, Category
from django.contrib.auth.models import User
import re

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    
    country = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Ghana, Nigeria, Kenya"}),
        help_text="Country of residence"
    )
    whatsapp_number = forms.CharField(
        max_length=20, required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+233 XX XXX XXXX"}),
        help_text="Used for order alerts & chat"
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Last name"}),
        }

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        "class": "form-control", "placeholder": "Username or Email", "autofocus": True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "Password"
    }))

class SellerSignupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}))
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current password'}),
        required=False, help_text='Leave blank to keep your current password'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password (if changed)'}),
        required=False, help_text='Only required if changing password'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        queryset = User.objects.filter(username=username)
        if self.user and self.user.is_authenticated:
            queryset = queryset.exclude(pk=self.user.pk)
        if queryset.exists():
            raise forms.ValidationError("This username is already taken.")
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        queryset = User.objects.filter(email=email)
        if self.user and self.user.is_authenticated:
            queryset = queryset.exclude(pk=self.user.pk)
        if queryset.exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password or password2:
            if password != password2:
                raise forms.ValidationError("Passwords don't match")
            if password and len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters")
        return password2

    store_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your store name'}))
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+233 XX XXX XXXX'}))
    whatsapp = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+233 XX XXX XXXX'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Your business address'}))
    region = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Region/State'}))

    class Meta:
        model = SellerProfile
        fields = ['store_name', 'phone', 'address', 'region']

class ProductUploadForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        empty_label="Select a category",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={"class": "form-control"}))
    
    # ✅ NEW: Size and Dimension Fields
    requires_size = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    size_stock_input = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'S:10, M:5, L:3 (comma-separated)'}),
        help_text="Format: Size:Quantity. e.g., S:10, M:5, 40:2"
    )
    length = forms.DecimalField(required=False, max_digits=8, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Length (cm)'}))
    width = forms.DecimalField(required=False, max_digits=8, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Width (cm)'}))
    height = forms.DecimalField(required=False, max_digits=8, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Height (cm)'}))

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'category', 'image', 'colors', 'warranty', 'vr_type',
                  'requires_size', 'size_stock_input', 'length', 'width', 'height']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Product description...'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity (0 if using sizes)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'colors': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Red, Blue, Black'}),
            'warranty': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1 Year Warranty'}),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '5'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Share your experience...'}),
        }

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your registered email'}))

class ResetPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password (min 8 characters)'}), min_length=8)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}))
    
    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            raise forms.ValidationError("Passwords don't match.")
        return cleaned