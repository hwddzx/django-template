#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.utils import timezone


class ActiveDataManager(models.Manager):
    def get_query_set(self):
        return super(ActiveDataManager, self).get_query_set().filter(is_active=True)

    def get_queryset(self):
        return super(ActiveDataManager, self).get_queryset().filter(is_active=True)


class TimeBaseModel(models.Model):
    created = models.DateTimeField(
        verbose_name='创建时间',
        default=timezone.now
    )

    updated = models.DateTimeField(
        verbose_name='更新时间',
        auto_now=True
    )

    def updated_timestamp(self):
        return int(self.updated.strftime("%s")) if self.updated else 0

    def created_timestamp(self):
        return int(self.created.strftime("%s")) if self.created else 0

    def get_etag(self):
        return str(self.updated_timestamp())

    class Meta:
        abstract = True


class BaseModel(TimeBaseModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='负责人',
        related_name='+',
        on_delete=models.CASCADE
    )

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        verbose_name='创建人',
        related_name='+',
        on_delete=models.CASCADE
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='激活状态'
    )

    objects = models.Manager()

    active_objects = ActiveDataManager()

    class Meta:
        abstract = True
