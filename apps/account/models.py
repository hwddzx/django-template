#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager

from apps.common.models import TimeBaseModel, BaseModel


class User(TimeBaseModel, PermissionsMixin, AbstractBaseUser):
    USER_ADMIN_ID = 1

    username = models.CharField(
        verbose_name=u'用户名',
        max_length=70,
        unique=True
    )

    email = models.EmailField(
        verbose_name=u'账号(邮箱地址)',
        blank=True,
        default=""
    )

    nickname = models.CharField(
        verbose_name=u'昵称',
        max_length=200,
        blank=True,
        default=""
    )

    phone = models.CharField(
        max_length=32,
        default='',
        verbose_name=u'电话',
        blank=True,
        db_index=True,
    )

    is_staff = models.BooleanField(
        'staff status',
        default=False,
    )
    is_active = models.BooleanField(
        'active',
        default=True,
    )

    date_joined = models.DateTimeField('date joined', default=timezone.now)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = u'用户'

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return self.nickname if self.nickname else self.username
