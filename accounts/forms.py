from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Profile
from .validators import validate_image

User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username', 'placeholder': 'Username'}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Password'}))


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=80, required=False, widget=forms.TextInput(attrs={'autocomplete': 'name', 'placeholder': 'Your full name'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'you@example.com (optional)'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'full_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username', 'autocomplete': 'username'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'At least 8 characters', 'autocomplete': 'new-password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Repeat your password', 'autocomplete': 'new-password'})
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm password'
        self.fields['username'].help_text = '150 characters or fewer. Letters, digits and @/./+/-/_ only.'

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('That username is already taken.')
        return username

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.filter(user=user).update(full_name=self.cleaned_data.get('full_name', '').strip())
        return user


class ProfileForm(forms.ModelForm):
    avatar = forms.ImageField(required=False, validators=[validate_image], widget=forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/gif,image/webp', 'data-image-input': ''}))
    remove_avatar = forms.BooleanField(required=False, label='Remove current picture')

    class Meta:
        model = Profile
        fields = ['full_name', 'bio', 'avatar', 'city', 'neighbourhood', 'interests', 'show_in_nearby']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell people a little about yourself', 'maxlength': 300}),
            'city': forms.TextInput(attrs={'placeholder': 'e.g. Lahore'}),
            'neighbourhood': forms.TextInput(attrs={'placeholder': 'e.g. Gulberg'}),
            'interests': forms.TextInput(attrs={'placeholder': 'photography, hiking, coffee'}),
        }
        labels = {'show_in_nearby': 'Show me on the Nearby page'}

    def clean_interests(self):
        items, seen = [], set()
        for raw in self.cleaned_data['interests'].split(','):
            item = raw.strip()
            if item and item.lower() not in seen:
                seen.add(item.lower())
                items.append(item)
        if len(items) > 10:
            raise forms.ValidationError('Please list at most 10 interests.')
        return ', '.join(items)

    def clean_city(self):
        return ' '.join(self.cleaned_data['city'].split())

    def clean_neighbourhood(self):
        return ' '.join(self.cleaned_data['neighbourhood'].split())

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.cleaned_data.get('remove_avatar') and not self.files.get('avatar'):
            profile.avatar.delete(save=False)
            profile.avatar = ''
        if commit:
            profile.save()
        return profile
