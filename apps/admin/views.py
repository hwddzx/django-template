#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View


class HomeView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(HomeView, self).dispatch(*args, **kwargs)

    """
    重定向到login页面
    """

    def get(self, request, *args, **kwargs):
        site_name = settings.SITE_NAME
        if request.user.is_authenticated:
            menus = self.build_menu()
            return render(request, 'admin/home.html', locals())

        # 如果没有登陆，返回默认的主页
        return redirect(reverse('admin:account:login'))

    def build_menu(self):
        SUBMENU_ACCOUNT = [
            (u'用户', reverse('admin:account:user_list'), lambda req: req.user.is_superuser),
            (u'用户组', reverse('admin:account:group_list'), lambda req: req.user.is_superuser),
        ]

        MENU = (
            {
                'menu': u'控制面板',
                'url': reverse('admin:dashboard'),
                'icon': 'fa fa-dashboard blue',
                'submenu': [],
                'permission': lambda req: req.user.is_staff
            },
            {
                'menu': u'系统管理',
                'url': '',
                'icon': 'fa fa-cogs',
                'submenu': SUBMENU_ACCOUNT
            },
        )

        menus = []
        for item in MENU:
            # check the top menu first.  not go into submenu if top menu is not permitted.
            if 'permission' in item:
                if not item['permission'](self.request):
                    continue

            has_permission = False
            menu = {"name": item['menu'], "url": item['url'], "icon": item['icon'], "submenus": []}
            for (name, url, permission_check) in item['submenu']:
                if permission_check is None or (permission_check and permission_check(self.request)):
                    has_permission = True
                    menu['submenus'].append({"name": name, "url": url})
            if has_permission or menu['url']:
                menus.append(menu)
        # remove menu with empty submenu
        return [menu for menu in menus if menu['url'] or menu['submenus']]


@login_required()
def dashboard(request):
    try:
        env_settings = os.environ['DJANGO_SETTINGS_MODULE']
    except KeyError:
        env_settings = "not define in env"

    # get which tag is using in current branch
    # cmd = 'cd %s && git describe --abbrev=0 --tags' % settings.SITE_ROOT
    active_settings = settings.SETTINGS_MODULE
    return render(request, 'admin/dashboard.inc.html', locals())

