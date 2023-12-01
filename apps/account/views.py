#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.urls import reverse
from django.contrib import auth
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import RedirectView
from django.views.generic.base import View, TemplateView

from apps.common import exceptions
from apps.account.forms import UserDatatablesBuilder, UserForm, UserChangePasswordForm
from apps.common.admin.views import NavigationHomeMixin, ModelAwareMixin, DatatablesBuilderMixin, AjaxDatatablesView, \
    RequestAwareMixin, AjaxUpdateView, AjaxSimpleUpdateView, AdminRequiredMixin, AjaxFormView


class LoginView(TemplateView):
    template_name = 'account/login.html'

    def post(self, request):
        result = exceptions.build_success_response_result()

        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        next_page = request.GET.get('next', '')
        user = auth.authenticate(username=username, password=password)
        if user:
            if not user.is_staff:
                auth.login(request, user)
                return redirect(reverse('website:home'))

            if user.is_active:
                auth.login(request, user)
                if next_page:
                    return redirect(next_page)
                else:
                    return redirect('/admin')
        else:
            result = exceptions.build_response_result(
                exceptions.ERROR_CODE_AUTH_FAILED)
        return render(request, 'account/login.html', locals())


class LogoutView(RedirectView):

    def get_redirect_url(self, **kwargs):
        auth.logout(self.request)
        return reverse('admin:account:login', args=kwargs)


class UserListView(NavigationHomeMixin, ModelAwareMixin, DatatablesBuilderMixin, AjaxDatatablesView):
    model = auth.get_user_model()
    datatables_builder_class = UserDatatablesBuilder
    queryset = auth.get_user_model().staffs.order_by('-date_joined')


class UserFormView(RequestAwareMixin, ModelAwareMixin, AjaxFormView):
    model = auth.get_user_model()
    model_name = 'user'
    template_name = 'account/user.form.inc.html'
    form_class = UserForm

    def get_context_data(self, **kwargs):
        context = super(UserFormView, self).get_context_data(**kwargs)
        if self.object:
            # only apply dummy password for the edit case.
            context['dummy_password'] = UserForm.DUMMY_PASSWORD
        return context


class UserLockView(AdminRequiredMixin, AjaxSimpleUpdateView):
    model = auth.get_user_model()

    def update(self, user):
        if self.request.user.id == user.id:
            return u"不允许自己锁定自己!"
        if user.is_superuser:
            return u"不允许锁定超级用户!"
        user.is_active = False
        user.save()


class UserUnlockView(AdminRequiredMixin, AjaxSimpleUpdateView):
    model = auth.get_user_model()

    def update(self, user):
        user.is_active = True
        user.save()


class UserChangePasswordView(ModelAwareMixin, RequestAwareMixin, AjaxUpdateView):
    model = auth.get_user_model()
    form_class = UserChangePasswordForm
    template_name = 'account/user.changepassword.inc.html'
    form_action_url_name = 'admin:account:change_password'

    def get_context_data(self, **kwargs):
        data = super(UserChangePasswordView, self).get_context_data(**kwargs)
        data['page_title'] = '修改密码'
        return data


class ForgetPasswordView(TemplateView):
    template_name = 'account/password_reset.html'


class ResetPasswordView(View):

    def post(self, request, *args, **kwargs):
        # email = request.POST['email']
        return JsonResponse(exceptions.build_success_response_result(), request)
