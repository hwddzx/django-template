#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.urls import path, include
from apps.admin import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='admin_home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('account/', include(('apps.account.urls', 'account'), namespace='account')),
]
