from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator
from django.forms.widgets import HiddenInput, NumberInput, Select
from django.utils.translation import gettext_lazy as _

from app_market.models import MessagesModel


User = get_user_model()


class CartForm2(forms.Form):
    instance_id = forms.IntegerField(label=_('Product id in the cart'), widget=HiddenInput)
    good_id = forms.IntegerField(label=_('Product id'), widget=HiddenInput)
    cat_id = forms.IntegerField(label=_('Category Id'), widget=HiddenInput)
    index = forms.IntegerField(label=_('the index of the form in the array'), widget=HiddenInput)
    image = forms.CharField(label=_('Picture'), widget=HiddenInput, required=False)
    title = forms.CharField(label=_('Product name'), widget=HiddenInput)
    price = forms.DecimalField(label=_('Product price'), widget=HiddenInput)
    discounted_price = forms.DecimalField(label=_('Product discount'), widget=HiddenInput, required=False)
    total_price = forms.DecimalField(label=_('Price for the whole product'), widget=HiddenInput)
    discounted_total_price = forms.DecimalField(
        label=_('The price for the whole product is discounted'), widget=HiddenInput, required=False)
    group_discount = forms.CharField(label=_('Discount'), required=False)
    catalog = forms.ChoiceField(widget=Select(attrs={'class': 'form-select', 'onchange': 'this.form.submit()'}))
    count = forms.IntegerField(
        widget=NumberInput(attrs={'class': 'Amount-input form-input', 'name': 'amount', 'type': 'text'}))


class AddGoodToCartWithCountForm(forms.Form):
    id = forms.IntegerField(widget=forms.HiddenInput)
    count = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={
        'class': 'Amount-input form-input', 'name': 'amount', 'type': 'text'
    }))

    def __init__(self, *args, **kwargs):
        """
        В инициаализации:
         - добавлен валидатор по максимальному количеству товара
        """
        super().__init__(*args, **kwargs)
        data = kwargs.get('initial')
        # добавим новые варианты выбора в choices
        if data:
            #     добавим новый валидатор
            max_count = data.get('max_count')
            if max_count:
                validator = MaxValueValidator(max_count)
                if validator not in self.fields['count'].validators:
                    self.fields['count'].validators.append(validator)


class OrderingForm(UserCreationForm, forms.ModelForm):
    full_name = forms.CharField(label=_('Full name'), max_length=100,
                                widget=forms.TextInput(attrs={'class': 'form-input',
                                                              'id': 'name',
                                                              'placeholder':
                                                                  'Иванов Иван Иванович',
                                                              'data-validate': 'require'}))
    phone = forms.CharField(label=_('Phone'), max_length=18, widget=forms.TextInput(
        attrs={'type': 'tel', 'class': 'form-input', 'id': 'phone',
               'placeholder': '+7 (123) 456-78-90', 'data-validate': 'require'}))
    email = forms.EmailField(label=_('E-mail'), widget=forms.TextInput(
        attrs={'class': 'form-input', 'id': 'mail',
               'placeholder': 'mail@example.com', 'data-validate': 'require'}))

    password1 = forms.CharField(label=_('Password'), max_length=50, widget=forms.TextInput(
        attrs={'type': 'password', 'class': 'form-input', 'id': 'password',
               'placeholder': _('password')}))
    password2 = forms.CharField(label=_('Confirm password'), max_length=50, widget=forms.TextInput(
        attrs={'type': 'password', 'class': 'form-input', 'id': 'passwordReply',
               'placeholder': _('confirm password')}))

    class Meta:
        model = User
        fields = ('username', 'full_name', 'phone', 'email', 'password1', 'password2')

    def clean_email(self):
        """
        Проверка на уникальность введенного email в БД
        """
        email = self.cleaned_data.get('email')

        try:
            if User.objects.get(email=email):
                raise forms.ValidationError(_('A user with such an email has already been registered'))
        except ObjectDoesNotExist:
            return email

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


class PayForm(forms.Form):
    """форма реализует поле оплаты в зависимости от типа оплаты"""
    pay_method = forms.CharField(max_length=20, widget=HiddenInput)
    order_id = forms.IntegerField(widget=HiddenInput)
    card_number = forms.CharField()
    card_number.widget.attrs.update({
        'class': "form-input Payment-bill",
        'id': "numero1",
        'name': "numero1", 'type': "text",
        'placeholder': "9999 9999",
        'data-mask': "9999 9999",
        'data-validate': "require pay"
    })


class MessagesForm(forms.ModelForm):
    name = forms.CharField(label=_('name'), widget=forms.TextInput(
        attrs={'name': 'name', 'class': 'form-input', 'placeholder': _('Name')}))
    mail = forms.EmailField(label=_('email'), widget=forms.EmailInput(
        attrs={'name': 'mail', 'class': 'form-input', 'placeholder': _('Email')}))
    website = forms.URLField(label=_('website'), widget=forms.URLInput(
        attrs={'name': 'website', 'class': 'form-input', 'placeholder': _('Website')}))
    message = forms.CharField(label=_('message'), widget=forms.Textarea(
        attrs={'name': 'message', 'class': 'form-textarea', 'placeholder': _('Message')}))

    class Meta:
        model = MessagesModel
        fields = ('name', 'mail', 'website', 'message')
