#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.urls import path
from apps.account import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('forget_password/', views.ForgetPasswordView.as_view(), name='forget_password'),
    path('reset_password/', views.ResetPasswordView.as_view(), name='reset_password'),

    path('user/list/', views.UserListView.as_view(), name='user_list'),
    path('user/list/.json/', views.UserListView.as_view(), name='user_list.json', kwargs={'json': True}),
    path('user/create/', views.UserFormView.as_view(), name='user_create', kwargs={'pk': 0}),
    path('user/<int:pk>/edit/', views.UserFormView.as_view(), name='user_edit'),
    path('user/<int:pk>/unlock/', views.UserLockView.as_view(), name='user_lock'),
    path('user/<int:pk>/lock/', views.UserUnlockView.as_view(), name='user_unlock'),
    path('user/<int:pk>/change_password/', views.UserChangePasswordView.as_view(), name='change_password'),
]
