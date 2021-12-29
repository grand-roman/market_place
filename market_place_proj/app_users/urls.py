from django.urls import path

from app_users import views


urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('account/', views.AccountView.as_view(), name='account'),
    path('account/profile/', views.ProfileView.as_view(), name='profile'),
    path('locale/<str:lang>', views.set_language, name='locale'),

    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),

    path('auth/password_change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('auth/password_change/done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    path('auth/password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('auth/password_reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),

    path('auth/reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/reset/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
