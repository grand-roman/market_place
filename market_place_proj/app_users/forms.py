from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.utils.translation import gettext_lazy as _


User = get_user_model()


class SignUpForm(UserCreationForm):
    error_css_class = 'is-invalid'

    username = forms.CharField(
        label=_('Username'),
        widget=forms.TextInput(attrs={
            'class': 'form-input',
        })
    )
    full_name = forms.CharField(
        label=_('Full name'),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
        })
    )
    email = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
        })
    )
    phone = forms.CharField(label=_('Phone'), max_length=18, required=True, widget=forms.TextInput(
        attrs={'type': 'tel', 'class': 'form-input', 'id': 'phone', 'placeholder': '+7 (123) 456-78-90'}))
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
        }),
        strip=False)
    password2 = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
        }),
        strip=False
    )

    class Meta:
        model = User
        fields = ('username', 'full_name', 'email', 'phone', 'password1', 'password2')

    def clean_phone(self):
        """
        Проверка на уникальность введенного телефона в БД,
        и корректность ввода должно быть 11 цифр.
        """
        phone = self.cleaned_data.get('phone')
        number_phone = ''.join([i for i in phone if i.isdigit()])

        try:
            match = User.objects.values('phone').get(phone=phone)
            if match:
                raise forms.ValidationError(_('User with this number is already registered.'))
        except User.DoesNotExist:
            if len(number_phone) == 1:
                raise forms.ValidationError(_('Obligatory field.'))
            elif len(number_phone) != 11:
                raise forms.ValidationError(_('Enter your phone number correctly.'))
            return number_phone


class ProfileForm(forms.ModelForm):
    error_css_class = 'is-invalid'

    full_name = forms.CharField(
        label=_('Full name'),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
        })
    )
    phone = forms.CharField(label=_('Phone'), max_length=18, required=True, widget=forms.TextInput(
        attrs={'type': 'tel', 'class': 'form-input', 'id': 'phone', 'placeholder': '+7 (123) 456-78-90'}))
    password1 = forms.CharField(
        label=_('Password'),
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
        }),
        strip=False)
    password2 = forms.CharField(
        label=_('Confirm password'),
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
        }),
        strip=False
    )

    class Meta:
        model = User
        fields = ('avatar', 'full_name', 'phone', 'email', 'password1', 'password2')
        widgets = {
            'avatar': forms.FileInput(attrs={'id': 'avatar', 'class': 'Profile-file form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'})
        }

    def clean_phone(self):
        """
        Проверка на уникальность введенного телефона в БД,
        и корректность ввода должно быть 11 цифр.
        """
        phone = self.cleaned_data.get('phone')
        number_phone = ''.join([i for i in phone if i.isdigit()])

        try:
            match = User.objects.values('phone').get(phone=phone)
            if match:
                raise forms.ValidationError(_('A user with such an email has already been registered'))
            if len(number_phone) == 1:
                raise forms.ValidationError(_('Required field.'))
            elif len(number_phone) != 11:
                raise forms.ValidationError(_('Enter the phone number correctly.'))

        except User.DoesNotExist:
            return number_phone


class LoginForm(forms.Form):
    username_log = UsernameField(
        label=_('Username'),
        widget=forms.TextInput(attrs={
            'class': 'form-input',
        })
    )
    password_log = forms.CharField(
        label=_('Password'),
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
        }),
        strip=False)

    def clean_password_log(self):
        username = self.cleaned_data.get('username_log')
        password = self.cleaned_data.get('password_log')

        user_cache = authenticate(username=username, password=password)
        if user_cache is None:
            raise forms.ValidationError(_('Invalid login or password'))
        else:
            self.cleaned_data['user'] = user_cache
        return password
