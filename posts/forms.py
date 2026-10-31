from django import forms

from accounts.validators import validate_image

from .models import Comment, Post

IMAGE_ACCEPT = 'image/jpeg,image/png,image/gif,image/webp'


class PostForm(forms.ModelForm):
    image = forms.ImageField(required=False, validators=[validate_image], widget=forms.FileInput(attrs={'accept': IMAGE_ACCEPT, 'data-image-input': '', 'id': 'id_image'}))
    remove_image = forms.BooleanField(required=False, label='Remove current image')

    class Meta:
        model = Post
        fields = ['text', 'image']
        widgets = {'text': forms.Textarea(attrs={'rows': 3, 'maxlength': 1000, 'placeholder': "What's happening in your neighbourhood?"})}

    def clean(self):
        cleaned = super().clean()
        text = (cleaned.get('text') or '').strip()
        keeps_image = bool(cleaned.get('image')) or (bool(self.instance.image) and not cleaned.get('remove_image'))
        if not text and not keeps_image and not self.errors:
            raise forms.ValidationError('Write something or attach an image to publish a post.')
        return cleaned

    def save(self, commit=True):
        post = super().save(commit=False)
        post.text = post.text.strip()
        if self.cleaned_data.get('remove_image') and not self.files.get('image'):
            post.image.delete(save=False)
            post.image = ''
        if commit:
            post.save()
        return post


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].error_messages['required'] = 'Comment cannot be empty.'

    def clean_text(self):
        text = self.cleaned_data['text'].strip()
        if not text:
            raise forms.ValidationError('Comment cannot be empty.')
        return text
