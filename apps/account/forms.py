#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django import forms
from django.contrib import auth
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, Permission

from apps.account.models import User
from apps.common import exceptions
from apps.common.admin.forms import CrispyModelForm
from apps.common.admin.datatables import DatatablesBuilder, DatatablesIdColumn, DatatablesTextColumn, \
    DatatablesBooleanColumn, DatatablesActionsColumn, DatatablesColumnActionsRender2


class UserForm(CrispyModelForm):
    # a dummy password to init to password editor of edit form
    DUMMY_PASSWORD = 'B5566AF90F4A'

    confirm_password = forms.CharField(
        label=u'确认密码',
        widget=forms.PasswordInput(
            attrs={
                'class': "required xlarge-input",
                'placeholder': u'确认密码，必填项'
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        self.fields['username'].widget.attrs['autofocus'] = "autofocus"

        if 'is_superuser' in self.fields:
            self.fields['is_superuser'].label = u'超级用户'

        self.fields['phone'].widget.attrs['data-regex'] = r'^1\d{10}$'

        if "password" in self.fields:
            self.fields['password'].widget = forms.PasswordInput(
                attrs={
                    'class': "required xlarge-input",
                    'placeholder': u'密码，必填项'
                }
            )
            self.fields['password'].label = u'密码'

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password != self.data.get('confirm_password'):
            raise forms.ValidationError(u"确认密码不一致")
        # it means user has changed the password if password is not dummy one
        if password != self.DUMMY_PASSWORD:
            password_hash = make_password(password)
        else:
            password_hash = self.instance.password
        return password_hash

    def save(self, commit=False):
        # 保存新用户的密码
        user = super(UserForm, self).save(commit)
        user.is_staff = True
        user.save()
        return user

    class Meta:
        model = auth.get_user_model()
        fields = (
            'username', 'phone', 'email', 'nickname', 'is_superuser', 'user_permissions', 'password',
            'confirm_password'
        )


class UserDatatablesBuilder(DatatablesBuilder):
    id = DatatablesIdColumn()

    username = DatatablesTextColumn(
        label=u'用户名',
        is_searchable=True,
        is_master_col=True
    )

    phone = DatatablesTextColumn(is_searchable=True)

    email = DatatablesTextColumn(is_searchable=True)

    nickname = DatatablesTextColumn(is_searchable=True)

    is_active = DatatablesBooleanColumn(
        (('', u'全部'), (1, u'激活'), (0, u'锁定')),
        label=u'状态',
        is_searchable=True,
        col_width='7%',
        search_expr=lambda value: Q(is_active=(True if value == '1' else False)),
        render=(lambda request, model, field_name:
                u'<span class="label label-info"> 启用 </span>' if model.is_active else
                u'<span class="label label-warning"> 禁用 </span>')
    )

    is_superuser = DatatablesBooleanColumn(
        label=u'管理员',
        col_width='5%',
        is_searchable=True,
        search_expr=lambda value: Q(is_superuser=(True if value == '1' else False))
    )

    @staticmethod
    def actions_render(request, model, field_name):
        actions = [
            {
                'is_link': True,
                'name': 'edit',
                'text': u'编辑',
                'icon': 'fa fa-edit',
                'url_name': 'admin:account:user_edit',
                'modal_show': True
            }
        ]

        if model.is_active:
            actions.append(
                {
                    'is_link': False,
                    'name': 'lock',
                    'text': u'锁定',
                    'icon': 'fa fa-lock',
                    'url_name': 'admin:account:user_lock'
                },
            )
        else:
            actions.append(
                {
                    'is_link': False,
                    'name': 'unlock',
                    'text': u'解锁',
                    'icon': 'fa fa-unlock',
                    'url_name': 'admin:account:user_unlock'
                }
            )
        return DatatablesColumnActionsRender2(actions).render(request, model, field_name)

    _actions = DatatablesActionsColumn(render=actions_render)

    class Meta:
        model = User


class GroupForm(CrispyModelForm):

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['permissions'].widget.attrs['class'] = "col-md-10"

    class Meta:
        model = Group
        fields = ('name', 'permissions')


class GroupDatatablesBuilder(DatatablesBuilder):
    id = DatatablesIdColumn()

    name = DatatablesTextColumn(label=u'名称', is_searchable=True)

    class Meta:
        model = Group


class UserChangePasswordForm(CrispyModelForm):
    old_password = forms.CharField(label=u'旧密码', required=True)

    new_password = forms.CharField(label=u'新密码', required=True)

    confirm_password = forms.CharField(label=u'确认密码', required=True)

    def __init__(self, *args, **kwargs):
        super(UserChangePasswordForm, self).__init__(*args, **kwargs)
        self.fields['old_password'].widget = forms.PasswordInput(
            attrs={'class': "required", 'placeholder': u'旧密码，必填项'}
        )
        self.fields['new_password'].widget = forms.PasswordInput(
            attrs={'class': "required", 'placeholder': u'新密码，必填项'}
        )
        self.fields['confirm_password'].widget = forms.PasswordInput(
            attrs={'class': "required", 'placeholder': u'再次输入密码，必填项'}
        )

    def clean(self):
        if any(self.errors):
            return ""
        cleaned_data = super(UserChangePasswordForm, self).clean()
        request_user = self.initial['request'].user
        result = None
        if cleaned_data['new_password'] != cleaned_data['confirm_password']:
            result = exceptions.build_response_result(exceptions.ERROR_CODE_NEW_PASSWORD_NOT_MATCH)
        else:
            if self.instance.id == request_user.id:
                # 修改自己的密码前需要先认证
                user = auth.authenticate(
                    username=request_user.username,
                    password=cleaned_data['old_password']
                )
                if not user:
                    result = exceptions.build_response_result(
                        exceptions.ERROR_CODE_AUTH_FAILED
                    )
            elif request_user.is_superuser:
                pass
            else:
                result = exceptions.build_response_result(exceptions.ERROR_CODE_PERMISSION_DENY)
        if result:
            raise forms.ValidationError(result['errmsg'])
        return cleaned_data

    def save(self, commit=False):
        user = super(UserChangePasswordForm, self).save(commit)
        user.set_password(self.cleaned_data['new_password'])
        user.save()
        return user

    class Meta:
        model = auth.get_user_model()
        fields = ('old_password', 'new_password', 'confirm_password')
