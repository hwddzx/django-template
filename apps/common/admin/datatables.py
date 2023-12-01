#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import datetime

from django import forms
from django.urls import reverse
from django.db.models import Q
from django.db.models import fields as d_fields
from django.contrib.auth import get_user_model
from django.utils.safestring import SafeString
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields.related import RelatedField

from apps.common import local_date_to_text, local_time_to_text


def number_search_expr(range, field_name):
    """
    支持按照数字过滤.
    value的格式如下: from-to
    10-80
    """
    q = Q()
    try:
        values = range.split('-')
        if values:
            filter = {"%s__gte" % field_name: int(values[0].strip())}
            q = Q(**filter)
            if len(values) == 2:
                filter = {"%s__lte" % field_name: int(values[1].strip())}
                q &= Q(**filter)
    except:
        pass
    return q


def date_search_expr(range, field_name):
    """
    支持按照数字过滤.
    value的格式如下: from-to
    20100102-20100102
    """
    q = Q()
    try:
        values = range.split('-')
        if values:
            from_time = datetime.datetime.strptime(values[0].strip(), '%Y%m%d')
            filter = {"%s__gte" % field_name: from_time}
            q = Q(**filter)
            if len(values) == 2:
                to_time = datetime.datetime.strptime(values[1].strip(), '%Y%m%d')
                to_time += datetime.timedelta(seconds=(24 * 3600 - 1))
                filter = {"%s__lte" % field_name: to_time}
                q &= Q(**filter)
    except:
        pass
    return q


class DatatablesColumnSimpleRender(object):
    def render(self, request, model, field_name):
        try:
            # noinspection PyProtectedMember
            model_field = model._meta.get_field(field_name)
        except FieldDoesNotExist as e:
            if hasattr(model, field_name):
                return getattr(model, field_name)()
            else:
                raise e
        # print model_field.attname, model_field.get_attname(), '=', getattr(obj, model_field.attname)
        val = model_field.value_to_string(model)
        if isinstance(model_field, RelatedField):
            if field_name == 'owner':
                val = model.owner.get_full_name() if model.owner else ""
            elif field_name == 'creator':
                val = model.creator.get_full_name() if model.creator else ""
            else:
                val = getattr(model, field_name)
        elif isinstance(model_field, d_fields.DecimalField):
            val = round(getattr(model, model_field.attname, 0), 2)
        elif isinstance(model_field, d_fields.DateTimeField):
            date = getattr(model, model_field.attname, None)
            val = local_time_to_text(date)
        elif isinstance(model_field, d_fields.DateField):
            date = getattr(model, model_field.attname, None)
            val = local_date_to_text(date)
        elif isinstance(model_field, d_fields.BooleanField):
            val = u'是' if val == 'True' else u'否'
        elif isinstance(model_field, d_fields.IntegerField) or isinstance(model_field, d_fields.CharField):
            if model_field.choices:
                display_method = getattr(model, 'get_%s_display' % model_field.attname, None)
                if display_method:
                    display = display_method()
                    if display:
                        val = display

        return val if val != "None" else ""


class DatatablesColumnActionsRender(object):
    DEFAULT_EXPAND_THRESHOLD = 5
    expand_threshold = DEFAULT_EXPAND_THRESHOLD

    def __init__(self, actions=None, action_permission=None):
        self.action_permission = action_permission
        if actions is None:
            self.actions = \
                [{'is_link': True, 'name': 'edit', 'text': u'编辑', 'icon': 'fa fa-edit'},
                 {'is_link': False, 'name': 'delete', 'text': u'删除', 'icon': 'fa fa-trash-o'}, ]
        else:
            self.actions = actions

    def render(self, request, model, field_name):
        if not self.actions:
            return ""

        if self.action_permission:
            has_permission = request.user.is_superuser or request.user.has_perm(self.action_permission)
            # If the user lacks the permission
            if not has_permission:
                return ""

        # noinspection PyProtectedMember
        namespace = "admin:" + model._meta.app_label
        # noinspection PyProtectedMember
        model_name = model._meta.object_name.lower()
        action_items = []
        for action in self.actions:
            is_link = action['is_link']
            new_window = action.get('new_window', False)
            name = action['name']
            url = action.get('url')
            if not url:
                url_name = action.get('url_name', '%s:%s_%s' % (namespace, model_name, name))
                url = reverse(url_name, kwargs={'pk': model.id})
            icon = action['icon']
            text = action['text']
            extra = action.get('extra') or {}
            extra_json = SafeString(json.dumps(extra))
            action_type = action.get('action_type') or 'GET'
            handler_type = action.get('handler_type') or 'system'
            modal_tag = "modal" if action.get('modal_show', False) else ""
            check_access = "data-check_access='true'" if action.get('check_access') else ""
            alert = action.get('alert', "")
            if is_link:
                if new_window and url:
                    template = u'''<a href="%(url)s" target="_blank" class='btn btn-sm btn-white btn-pink'> <i class='%(icon)s'></i>%(text)s</a>'''
                else:
                    template = u'''
    <a href='#' data-action='%(name)s' data-extra='%(extra_json)s' data-text='%(text)s' data-%(modal_tag)surl='%(url)s' class='btn btn-sm btn-white btn-pink' \
    data-handlertype='%(handler_type)s' %(check_access)s> <i class='%(icon)s'></i> %(text)s</a>'''
            else:
                template = u'''
<a href='#action' data-action='%(name)s' data-extra='%(extra_json)s' data-text='%(text)s' class='btn btn-sm btn-white btn-pink' \
data-actiontype='%(action_type)s' data-%(modal_tag)surl='%(url)s' data-alert='%(alert)s' data-handlertype='%(handler_type)s' %(check_access)s> \
<i class='%(icon)s'></i> %(text)s</a>'''
            action_items.append(template % locals())

        actions_str = ""

        if self.expand_threshold < len(self.actions):
            for item in action_items:
                actions_str += "<li>" + item + "</li>"
            html = u'''
<div class="btn-group">
  <button data-toggle="dropdown" class="btn btn-primary dropdown-toggle btn-sm">操作<span class="caret"></span></button>
  <ul class="pull-right dropdown-menu action-button">%s</ul>
</div>'''
        else:
            actions_str = "".join(action_items)
            html = u'<div class="btn-group">%s</div>'

        return html % actions_str


class DatatablesColumnActionsRender2(object):
    """
    使用更紧凑的方式显示操作, 只显示图标, 不显示文字. 文字通过hint方式显示.
    """
    DEFAULT_EXPAND_THRESHOLD = 2
    expand_threshold = DEFAULT_EXPAND_THRESHOLD

    def __init__(self, actions=None, action_permission=None):
        self.action_permission = action_permission
        if actions is None:
            self.actions = [
                {
                    'is_link': True,
                    'name': 'edit',
                    'text': u'编辑',
                    'icon': 'fa fa-edit'
                },
                {
                    'is_link': False,
                    'name': 'delete',
                    'text': u'删除',
                    'icon': 'fa fa-trash-o'
                }
            ]
        else:
            self.actions = actions

    def render(self, request, model, field_name):
        if not self.actions:
            return ""

        if self.action_permission:
            has_permission = request.user.is_superuser or request.user.has_perm(self.action_permission)
            # If the user lacks the permission
            if not has_permission:
                return ""
        if hasattr(model, '_meta'):
            # noinspection PyProtectedMember
            namespace = "admin:" + model._meta.app_label
            # noinspection PyProtectedMember
            model_name = model._meta.object_name.lower()
        else:
            namespace = ''
            model_name = ''

        action_items = []
        colors = ('blue', 'green', 'red')
        for (index, action) in enumerate(self.actions):
            is_link = action['is_link']
            new_window = action.get('new_window', False)
            name = action['name']
            url = action.get('url')
            if not url:
                url_name = action.get('url_name', '%s:%s_%s' % (namespace, model_name, name))
                url = reverse(url_name, kwargs={'pk': model.id})
            icon = action['icon']
            text = action['text']
            extra = action.get('extra') or {}
            extra_json = SafeString(json.dumps(extra))
            action_type = action.get('action_type') or 'GET'
            handler_type = action.get('handler_type') or 'system'
            modal_tag = "modal" if action.get('modal_show', False) else ""
            check_access = "data-check_access='true'" if action.get('check_access') else ""
            color = colors[index % len(colors)]
            attrs = action.get('attrs', '')
            alert = action.get('alert', "")
            if is_link:
                if new_window and url:
                    template = u'''<a href="%(url)s" target="_blank" class='%(color)s' title='%(text)s'> <i class='ace-icon bigger-130 %(icon)s'></i></a>'''
                else:
                    template = u'''
    <a href='#' data-action='%(name)s' data-extra='%(extra_json)s' data-text='%(text)s' data-%(modal_tag)surl='%(url)s' class='%(color)s' \
    data-handlertype='%(handler_type)s' %(check_access)s  title='%(text)s' %(attrs)s> <i class='ace-icon bigger-130 %(icon)s'></i></a>'''
            else:
                template = u'''
<a href='#action' data-action='%(name)s' data-extra='%(extra_json)s' data-text='%(text)s' class='%(color)s' \
data-actiontype='%(action_type)s' data-%(modal_tag)surl='%(url)s' data-handlertype='%(handler_type)s' data-alert='%(alert)s' title='%(text)s' %(check_access)s  %(attrs)s> \
<i class='ace-icon bigger-130 %(icon)s'></i></a>'''
            action_items.append(template % locals())

        actions_str = "".join(action_items)
        html = u'<div class="action-buttons">%s</div>'

        return html % actions_str


class DatatablesColumnActionsFlatRender(object):
    """
    使用紧凑的方式显示操作, 显示图标+文字的button
    注意button的颜色和大小需要通过css的class来指定：
    - btn-success 绿色
    - btn-info    浅蓝
    - btn-primary 深蓝
    - btn         灰色
    - btn-warning 桔红
    - btn-danger  红色

    - btn-minier 最小
    - btn-xs     较小
    - btn-small  小
    """
    DEFAULT_EXPAND_THRESHOLD = 2
    expand_threshold = DEFAULT_EXPAND_THRESHOLD

    def __init__(self, actions=None, action_permission=None, multiple_line=False):
        self.action_permission = action_permission
        self.multiple_line = multiple_line
        if actions is None:
            self.actions = \
                [{'is_link': True, 'name': 'edit', 'text': u'编辑', 'icon': 'fa fa-edit'},
                 {'is_link': False, 'name': 'delete', 'text': u'删除', 'icon': 'fa fa-trash-o'}, ]
        else:
            self.actions = actions

    def render(self, request, model, field_name):
        if not self.actions:
            return ""

        if self.action_permission:
            has_permission = request.user.is_superuser or request.user.has_perm(self.action_permission)
            # If the user lacks the permission
            if not has_permission:
                return ""

        # noinspection PyProtectedMember
        namespace = "admin:" + model._meta.app_label
        # noinspection PyProtectedMember
        model_name = model._meta.object_name.lower()
        action_items = []
        for (index, action) in enumerate(self.actions):
            is_link = action['is_link']
            name = action['name']
            url = action.get('url')
            if not url:
                url_name = action.get('url_name', '%s:%s_%s' % (namespace, model_name, name))
                url = reverse(url_name, kwargs={'pk': model.id})
            icon = action['icon']
            text = action['text']
            css_class = action['css_class']
            extra = action.get('extra') or {}
            extra_json = SafeString(json.dumps(extra))
            action_type = action.get('action_type') or 'GET'
            handler_type = action.get('handler_type') or 'system'
            modal_tag = "modal" if action.get('modal_show', False) else ""
            check_access = "data-check_access='true'" if action.get('check_access') else ""
            attrs = action.get('attrs', '')
            alert = action.get('alert', "")
            if is_link:
                template = u'''
<a href='#' data-action='%(name)s' data-extra='%(extra_json)s' data-text='%(text)s' data-%(modal_tag)surl='%(url)s' style="margin: 3px 3px !important;" class='%(css_class)s' \
data-handlertype='%(handler_type)s' %(check_access)s %(attrs)s> <i class='ace-icon bigger-130 %(icon)s'></i> %(text)s</a>'''
            else:
                template = u'''
<a href='#action' data-action='%(name)s' data-extra='%(extra_json)s' data-text='%(text)s' style="margin: 3px 3px !important;" class='%(css_class)s' \
data-actiontype='%(action_type)s' data-%(modal_tag)surl='%(url)s' data-handlertype='%(handler_type)s' data-alert='%(alert)s' %(check_access)s %(attrs)s> \
<i class='ace-icon bigger-130 %(icon)s'></i> %(text)s</a>'''
            if self.multiple_line:
                template += u'<br/>'

            action_items.append(template % locals())

        actions_str = "".join(action_items)
        html = u'<div class="action-buttons">%s</div>'

        return html % actions_str


class DatatablesColumnImageRender(object):

    def render(self, request, model, field_name):
        if hasattr(model, field_name):
            attr = getattr(model, field_name)

            if callable(attr):
                url = attr()
            else:
                url = attr.url if attr else ""
        else:
            raise NotImplemented("Invalid field name for image ")
        if url:
            return '<a href="%s" target="_blank"> <img class="small-icon" src="%s"></a>' % (url, url)
        return ""


class DatatablesColumnDateRender(object):

    def render(self, request, model, field_name):
        if hasattr(model, field_name):
            attr = getattr(model, field_name)
            if callable(attr):
                date = attr()
            else:
                date = attr
        else:
            raise NotImplemented("Invalid field for date ")
        return local_date_to_text(date)


class DatatablesColumnMixin(object):
    def __init__(self, *args, **kwargs):
        self.is_sortable = kwargs.pop('is_sortable', False)
        self.is_visible = kwargs.pop('is_visible', True)
        self.is_searchable = kwargs.pop('is_searchable', False)
        self.col_width = kwargs.pop('col_width', '')
        self.search_expr = kwargs.pop('search_expr', '')
        self.css_class = kwargs.pop('css_class', '')
        self.render = kwargs.pop('render', DatatablesColumnSimpleRender())
        self.is_checkbox = kwargs.pop('is_checkbox', False)
        # alert message will use the text from master column.
        self.is_master_col = kwargs.pop('is_master_col', False)
        self.sorting_field = kwargs.pop('sorting_field', '')
        self.is_index_col = kwargs.pop('is_index_col', False)
        self.placeholder = kwargs.pop('placeholder', None)
        super(DatatablesColumnMixin, self).__init__(*args, **kwargs)


class DatatablesTextColumn(DatatablesColumnMixin, forms.CharField):
    def __init__(self, *args, **kwargs):
        link_resolve = kwargs.pop('link_resolve', None)
        modal_flag = ""
        if not link_resolve:
            link_resolve = kwargs.pop('modal_link_resolve', None)
            modal_flag = "modal"
        if link_resolve:
            if kwargs.pop('access_check', None):
                url_tag = '<a href="#" data-check_access="true" data-' + modal_flag + 'url="%s">%s</a>'
            else:
                url_tag = '<a href="#" data-' + modal_flag + 'url="%s">%s</a>'
            kwargs['render'] = kwargs.get('render', (
                lambda request, model, field_name: url_tag % link_resolve(request, model, field_name)))

        super(DatatablesTextColumn, self).__init__(*args, **kwargs)
        self.widget.attrs['class'] = self.css_class or 'input-small'


class DatatablesModelChoiceColumn(DatatablesColumnMixin, forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs['is_sortable'] = kwargs.get('is_sortable', True)
        super(DatatablesModelChoiceColumn, self).__init__(*args, **kwargs)


class DatatablesUserChoiceColumn(DatatablesModelChoiceColumn):
    def __init__(self, *args, **kwargs):
        super(DatatablesUserChoiceColumn, self).__init__(is_searchable=True,
                                                         queryset=get_user_model().staffs.active_objects().only('name'),
                                                         col_width="6%",
                                                         *args, **kwargs)

    def label_from_instance(self, obj):
        return obj.get_full_name()


class DatatablesChoiceColumn(DatatablesColumnMixin, forms.MultipleChoiceField):

    def __init__(self, choices, *args, **kwargs):
        kwargs['choices'] = choices
        super(DatatablesChoiceColumn, self).__init__(*args, **kwargs)


class DatatablesBooleanColumn(DatatablesColumnMixin, forms.ChoiceField):

    def __init__(self, choices=None, *args, **kwargs):
        kwargs['choices'] = choices or (('', u'全部'), (1, u'是'), (0, '否'))
        kwargs['is_sortable'] = kwargs.get('is_sortable', True)
        super(DatatablesBooleanColumn, self).__init__(*args, **kwargs)


class DatatablesDateTimeColumn(DatatablesColumnMixin, forms.DateTimeField):

    def __init__(self, *args, **kwargs):
        kwargs['col_width'] = kwargs.get('col_width', "8%")
        kwargs['is_sortable'] = kwargs.get('is_sortable', True)
        kwargs['placeholder'] = kwargs.get('placeholder', datetime.datetime.now().strftime('%Y%m%d'))
        super(DatatablesDateTimeColumn, self).__init__(*args, **kwargs)
        self.widget.attrs['class'] = self.css_class or 'input-small'


class DatatablesDateColumn(DatatablesColumnMixin, forms.DateField):

    def __init__(self, *args, **kwargs):
        kwargs['col_width'] = kwargs.get('col_width', "8%")
        kwargs['is_sortable'] = kwargs.get('is_sortable', True)
        kwargs['render'] = kwargs.get('render') or DatatablesColumnDateRender()
        kwargs['placeholder'] = kwargs.get('placeholder', datetime.datetime.now().strftime('%Y%m%d'))
        super(DatatablesDateColumn, self).__init__(*args, **kwargs)
        self.widget.attrs['class'] = self.css_class or 'input-small'


class DatatablesImageColumn(DatatablesTextColumn):

    def __init__(self, *args, **kwargs):
        kwargs['col_width'] = kwargs.get('col_width', "5%")
        kwargs['render'] = kwargs.get('render') or DatatablesColumnImageRender()
        super(DatatablesImageColumn, self).__init__(*args, **kwargs)


class DatatablesIntegerColumn(DatatablesTextColumn):

    def __init__(self, *args, **kwargs):
        kwargs['col_width'] = kwargs.get('col_width', "5%")
        super(DatatablesIntegerColumn, self).__init__(*args, **kwargs)


class DatatablesIdColumn(DatatablesTextColumn):

    def __init__(self, *args, **kwargs):
        kwargs['col_width'] = kwargs.get('col_width', "3%")
        kwargs['is_visible'] = kwargs.get('is_visible', False)
        kwargs['is_searchable'] = kwargs.get('is_searchable', True)
        kwargs['search_expr'] = kwargs.get('search_expr') or (lambda value: Q(id=value))
        super(DatatablesIdColumn, self).__init__(*args, label='ID', **kwargs)


class DatatablesActionsColumn(DatatablesColumnMixin, forms.CharField):

    def __init__(self, *args, **kwargs):
        # set a default render
        kwargs['render'] = kwargs.get('render', DatatablesColumnActionsRender(actions=kwargs.pop("actions", None),
                                                                              action_permission=kwargs.pop(
                                                                                  "action_permission", None)), )
        kwargs['col_width'] = kwargs.get('col_width', "8%")
        super(DatatablesActionsColumn, self).__init__(*args, label='', **kwargs)


class DatatablesCheckboxColumn(DatatablesColumnMixin, forms.CharField):

    def __init__(self, *args, **kwargs):
        # set a default render
        kwargs['render'] = kwargs.get('render', (lambda request, model, field_name:
                                                 '<input type="checkbox" name="id-%s-%d" data-id="%s" /><span class="lbl"></span>' % (
                                                     field_name, model.id, model.id)))
        kwargs['col_width'] = kwargs.get('col_width', "2%")
        kwargs['is_checkbox'] = kwargs.get('is_checkbox', True)

        super(DatatablesCheckboxColumn, self).__init__(*args, label=' ', **kwargs)


class DatatablesIndexColumn(DatatablesColumnMixin, forms.CharField):

    def __init__(self, *args, **kwargs):
        # set a default render
        kwargs['render'] = kwargs.get('render', (lambda request, model, field_name: ""))
        kwargs['col_width'] = kwargs.get('col_width', "1%")
        kwargs['is_index_col'] = kwargs.get('is_index_col', True)
        super(DatatablesIndexColumn, self).__init__(*args, label=' ', **kwargs)


class DatatablesBuilder(forms.Form):

    def build_aoColumnDefs(self):
        """
        see http://www.datatables.net/usage/columns
        """
        ret = []
        index = 0
        for name, field in self.fields.items():
            label = field.label
            is_sys_field = name.startswith("_")
            if not label and not is_sys_field:
                # noinspection PyProtectedMember
                label = self.Meta.model._meta.get_field(name).verbose_name
            entry = {'name': name, 'title': label, 'orderable': field.is_sortable,
                     'visible': field.is_visible, 'targets': [index], 'data': name,
                     'searchable': field.is_searchable, }
            if field.is_master_col:
                entry['className'] = 'datatables-master-column'
            if field.is_index_col:
                entry['className'] = 'datatables-index-column'
            if field.col_width:
                entry['width'] = field.col_width
            if field.placeholder:
                entry['placeholder'] = field.placeholder
            ret.append(entry)
            index += 1
        return SafeString(json.dumps(ret))


class DatatablesItemsColumn(DatatablesColumnMixin, forms.CharField):

    def __init__(self, *args, **kwargs):
        # set a default render
        kwargs['render'] = kwargs.get('render', DatatablesColumnItemsRender(items=kwargs.pop("items", None)))
        kwargs['col_width'] = kwargs.get('col_width', "5%")
        super(DatatablesItemsColumn, self).__init__(*args, **kwargs)


class DatatablesColumnItemsRender(object):
    def __init__(self, items=None):
        self.items = items

    def render(self, request, model):
        if not self.items:
            return ""

        # noinspection PyProtectedMember
        namespace = "admin:" + model._meta.app_label
        # noinspection PyProtectedMember
        model_name = model._meta.object_name.lower()
        count = "%s" % len(self.items)
        item_list = ""
        for item in self.items:
            name = item['name']
            url = item.get('url')
            if not url:
                url_name = item.get('url_name', '%s:%s_%s' % (namespace, model_name, name))
                url = reverse(url_name, kwargs={'pk': item['id']})
            text = item['text']
            check_access = "data-check_access='true'" if item.get('check_access') else ""

            template = u'''
<li><a href='#' data-action='%(name)s' data-text='%(text)s' data-url='%(url)s' %(check_access)s> %(text)s</a></li>'''
            item_list += template % locals()
        html = u'''
<div class="btn-group">
  <button data-toggle="dropdown" class="btn btn-yellow dropdown-toggle btn-sm">%s<span class="caret"></span></button>
  <ul class="pull-right dropdown-menu action-button">%s</ul>
</div>'''
        return html % (count, item_list)


class DatatablesUrlLinkColumn(DatatablesColumnMixin, forms.CharField):

    def __init__(self, *args, **kwargs):
        link_resolve = kwargs.pop('link_resolve', None)
        url_tag = '<a href="%s" target="_blank">%s</a>'
        kwargs['render'] = kwargs.get('render', (
            lambda request, model, field_name: url_tag % link_resolve(request, model, field_name)))
        super(DatatablesUrlLinkColumn, self).__init__(*args, **kwargs)
