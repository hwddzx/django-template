#!/usr/bin/env python
# -*- coding: utf-8 -*-

def get_field_max_length(model, field_name):
    # noinspection PyProtectedMember
    return model._meta.get_field(field_name).max_length


def local_time_to_text(local_time):
    # it make no sense to be precise to seconds
    return local_time.strftime("%Y-%m-%d %H:%M") if local_time else ""


def local_date_to_text(local_time):
    # it make no sense to be precise to seconds
    return local_time.strftime("%Y-%m-%d") if local_time else ""
