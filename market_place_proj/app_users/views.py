from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView as BaseLoginView,
    LogoutView as BaseLogoutView,
    PasswordChangeDoneView as BasePasswordChangeDoneView,
    PasswordChangeView as BasePasswordChangeView,
    PasswordResetCompleteView as BasePasswordResetCompleteView,
    PasswordResetConfirmView as BasePasswordResetConfirmView,
    PasswordResetDoneView as BasePasswordResetDoneView,
    PasswordResetView as BasePasswordResetView,
)
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy, translate_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import LANGUAGE_SESSION_KEY, check_for_language, gettext_lazy as _
from django.views.generic import CreateView, DetailView, UpdateView

from app_market.models import Order
from app_users.forms import ProfileForm, SignUpForm
from app_users.mixins import AuthBaseBreadcrumbMixin


LANGUAGE_QUERY_PARAMETER = 'language'


def set_language(request, lang):
    """Функция для изменения языка сайта."""

    next_url = request.GET.get('next', request.GET.get('next'))
    schema = url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )
    if (next_url or request.accepts('text/html')) and not schema:
        next_url = request.META.get('HTTP_REFERER')
        next_url = next_url and unquote(next_url)
        if not schema:
            next_url = '/'
    response = HttpResponseRedirect(next_url) if next_url else HttpResponse(status=204)
    if request.method == 'GET':
        lang_code = lang if lang else LANGUAGE_QUERY_PARAMETER
        if lang_code and check_for_language(lang_code):
            if next_url:
                next_trans = translate_url(next_url, lang_code)
                if next_trans != next_url:
                    response = HttpResponseRedirect(next_trans)
            if hasattr(request, 'session'):
                request.session[LANGUAGE_SESSION_KEY] = lang_code
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME, lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
    return response


class LoginView(AuthBaseBreadcrumbMixin, BaseLoginView):
    breadcrumbs = [(_('Log in'), reverse_lazy('login'))]


class LogoutView(AuthBaseBreadcrumbMixin, BaseLogoutView):
    breadcrumbs = [(_('Log out'), reverse_lazy('logout'))]


class PasswordChangeView(AuthBaseBreadcrumbMixin, BasePasswordChangeView):
    breadcrumbs = [(_('Password change'), reverse_lazy('password_change'))]


class PasswordChangeDoneView(AuthBaseBreadcrumbMixin, BasePasswordChangeDoneView):
    breadcrumbs = [(_('Password change'), reverse_lazy('password_change_done'))]


class PasswordResetView(AuthBaseBreadcrumbMixin, BasePasswordResetView):
    breadcrumbs = [(_('Password reset'), reverse_lazy('password_reset'))]


class PasswordResetDoneView(AuthBaseBreadcrumbMixin, BasePasswordResetDoneView):
    breadcrumbs = [(_('Password reset confirmation'), reverse_lazy('password_reset_done'))]


class PasswordResetConfirmView(AuthBaseBreadcrumbMixin, BasePasswordResetConfirmView):
    breadcrumbs = [(_('Password reset confirmation'), reverse_lazy('password_reset_confirm'))]


class PasswordResetCompleteView(AuthBaseBreadcrumbMixin, BasePasswordResetCompleteView):
    breadcrumbs = [(_('Password reset'), reverse_lazy('password_reset_complete'))]


class SignupView(AuthBaseBreadcrumbMixin, CreateView):
    """Представление для регистрации."""
    form_class = SignUpForm
    template_name = 'app_users/signup.html'
    breadcrumbs = [(_('Sign up'), reverse_lazy('signup'))]

    def get_success_url(self) -> str:
        return reverse_lazy('index')

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.save()

        username = form.cleaned_data.get('username')
        raw_password = form.cleaned_data.get('password1')
        user = authenticate(username=username, password=raw_password)
        login(self.request, user)

        return redirect(self.get_success_url())


class AccountView(LoginRequiredMixin, AuthBaseBreadcrumbMixin, DetailView):
    """Представление для аккаунта пользователя."""
    login_url = reverse_lazy('login')
    home_label = _('Home')
    template_name = 'app_users/account.html'
    breadcrumbs = [(_('Account'), reverse_lazy('account'))]

    def get_object(self, queryset=None):
        return self.request.user

    def get_queryset(self, **kwargs):
        queryset = Order.objects.filter(user=self.request.user).order_by('-pk').first()
        return queryset


class ProfileView(LoginRequiredMixin, AuthBaseBreadcrumbMixin, UpdateView):
    """Представление для профиля пользователя."""
    form_class = ProfileForm
    login_url = reverse_lazy('login')
    template_name = 'app_users/profile.html'
    success_url = 'profile'
    breadcrumbs = [(_('Profile'), reverse_lazy('profile'))]

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        password1 = form.cleaned_data.pop('password1', None)
        password2 = form.cleaned_data.pop('password2', None)
        if password1 and password2:
            user = form.instance
            user.password = user.set_password(password1)
            user.save()
        super(ProfileView, self).form_valid(form)
        return redirect(self.success_url)
