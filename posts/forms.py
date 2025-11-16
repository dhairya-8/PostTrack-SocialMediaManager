# posts/forms.py

from django import forms
from .models import Post, PostRequest, Rating
from users.models import ClientProfile

class PostCreationForm(forms.ModelForm):
    
    assigned_client = forms.ModelChoiceField(
        queryset=ClientProfile.objects.all(),
        label="Assign to Client",
        empty_label="Select a Client"
    )

    class Meta:
        model = Post
        fields = ['title', 'caption', 'image', 'scheduled_datetime', 'assigned_client']
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'caption': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            
            # --- 1. UPDATED THIS WIDGET ---
            'image': forms.FileInput(attrs={'class': 'form-control', 'id': 'id_image_input'}),
            
            # --- 2. UPDATED THIS WIDGET ---
            'scheduled_datetime': forms.DateTimeInput(
                attrs={
                    'class': 'form-control', 
                    'type': 'text',  # Changed from 'datetime-local'
                    'placeholder': 'Select Date and Time',
                    'data-toggle': 'flatpickr' # Added a hook for our JS
                }
            ),
            'assigned_client': forms.Select(attrs={'class': 'form-select'}),
        }
        
# --- POST EDIT FORM ---
class PostEditForm(forms.ModelForm):
    """
    Form for editing an existing post.
    """
    assigned_client = forms.ModelChoiceField(
        queryset=ClientProfile.objects.all(),
        label="Assign to Client",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Post
        fields = ['title', 'caption', 'image', 'scheduled_datetime', 'assigned_client']
        
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'caption': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            
            # --- 1. UPDATED THIS WIDGET ---
            'image': forms.FileInput(attrs={'class': 'form-control', 'id': 'id_image_input'}),
            
            # --- 2. UPDATED THIS WIDGET ---
            'scheduled_datetime': forms.DateTimeInput(
                attrs={
                    'class': 'form-control', 
                    'type': 'text', # Changed from 'datetime-local'
                    'placeholder': 'Select Date and Time',
                    'data-toggle': 'flatpickr' # Added a hook for our JS
                }
            ),
        }
        
# --- POST REQUEST FORM (for clients) ---
class PostRequestForm(forms.ModelForm):
    class Meta:
        model = PostRequest
        fields = ['desired_date', 'request_details']
        
        widgets = {
            'desired_date': forms.DateInput(
                attrs={
                    'class': 'form-control', 
                    'type': 'date' # This gives a nice date picker
                }
            ),
            'request_details': forms.Textarea(
                attrs={
                    'class': 'form-control', 
                    'rows': 6,
                    'placeholder': 'Please provide details about your post request. e.g., "A post for our new product launch," "A holiday greeting for Christmas," etc.'
                }
            ),
        }
        labels = {
            'desired_date': 'Desired Post Date (Optional)',
            'request_details': 'What should this post be about?'
        }
        
# --- REPLACED: CLIENT RATING FORM ---
class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['score', 'comment']
        widgets = {
            # 1. 'score' is now a hidden field. JS will control it.
            'score': forms.HiddenInput(attrs={'id': 'id_score', 'value': '0'}),
            
            # 2. 'comment' widget remains the same
            'comment': forms.Textarea(
                attrs={
                    'class': 'form-control', 
                    'rows': 3, 
                    'placeholder': 'Add an optional comment...'
                }
            ),
        }
        labels = {
            'comment': 'Add a Comment'
        }