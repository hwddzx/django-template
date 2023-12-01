#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone
from django.db.models import Prefetch
from django.contrib.auth.models import UserManager, AbstractBaseUser, PermissionsMixin

from apps.common.models import TimeBaseModel, BaseModel


class StaffManager(models.Manager):
    def get_queryset(self):
        return super(StaffManager, self).get_queryset().filter(is_staff=True).exclude(id=User.USER_ADMIN_ID)

    def active_objects(self):
        return self.get_queryset().filter(is_active=True)


class UserBaseInfoQuerySet(models.QuerySet):

    def names_prefetch(self, related_field_name):
        return Prefetch(related_field_name, queryset=self.names())

    def names(self):
        return self.filter().only('nick_name', 'username', 'phone')


class User(TimeBaseModel, PermissionsMixin, AbstractBaseUser):
    USER_ADMIN_ID = 1

    username = models.CharField(verbose_name=u'用户名',
                                max_length=70,
                                unique=True)

    email = models.EmailField(verbose_name=u'账号(邮箱地址)',
                              blank=True,
                              default="")

    nick_name = models.CharField(verbose_name=u'姓名',
                                 max_length=200,
                                 blank=True,
                                 default="")

    phone = models.CharField(max_length=32,
                             default='',
                             verbose_name=u'电话',
                             db_index=True)

    is_staff = models.BooleanField('staff status',
                                   default=False,
                                   help_text='Designates whether the user can log into this admin site.')
    is_active = models.BooleanField('active',
                                    default=True,
                                    help_text='Designates whether this user should be treated as '
                                              'active. Unselect this instead of deleting accounts.')

    date_joined = models.DateTimeField('date joined', default=timezone.now)

    objects = UserManager()
    staffs = StaffManager()
    base_info_objects = UserBaseInfoQuerySet.as_manager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = u'用户'

    def get_full_name(self):
        return self.nick_name if self.nick_name else self.username

    def __unicode__(self):
        return self.get_full_name()
