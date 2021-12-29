from django import forms


class ImportFileForm(forms.Form):
    files = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'multiple': True}))
    email = forms.EmailField(max_length=100, required=False)
