from django import forms
from .models import User


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = (
            'external_id',
            'name'
        )
        widgets = {
            'name': forms.TextInput,
        }