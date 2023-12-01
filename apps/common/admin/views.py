#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import logging
import datetime
import urllib

from io import StringIO
from collections import OrderedDict

from xlsxwriter.workbook import Workbook

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils.html import escape
from django.forms import CharField, ChoiceField
from django.urls import reverse, NoReverseMatch
from django.db.models import fields as d_fields
from django.shortcuts import get_object_or_404, render
from django.db.models.fields.related import RelatedField
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import ContextMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.core.exceptions import ImproperlyConfigured, ValidationError, FieldDoesNotExist

from crispy_forms.helper import FormHelper

from apps.common import exceptions, local_time_to_text
from apps.common.admin.forms import ModelDetail

HERE = os.path.dirname(__file__)
logger = logging.getLogger('apps.' + os.path.basename(os.path.dirname(HERE)) + '.' + os.path.basename(HERE))


class ActionUrlBuilderMixin(object):
    root_namespace = None

    def get_action_url(self, model, action):
        # noinspection PyProtectedMember
        model_meta = model._meta
        namespace = getattr(self, 'app_label', None)
        if namespace is None:
            namespace = model_meta.app_label
        namespace = "%s%s" % (self.root_namespace, ":" + namespace if namespace else "")
        model_name = getattr(self, 'model_name', None)
        if not model_name:
            model_name = model_meta.object_name.lower()
        return '%s:%s_%s' % (namespace, model_name, action)


class AjaxLoginRequiredMixin(object):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise exceptions.AjaxAuthRequired()
        return super(AjaxLoginRequiredMixin, self).dispatch(request, *args, **kwargs)


class AdminRequiredMixin(object):
    """
    Mixin allows you to require a user with `is_superuser` set to True.
    """

    def dispatch(self, request, *args, **kwargs):
        # If the user is a supper user,
        if not request.user.is_superuser:
            raise exceptions.AjaxPermissionDeny()
        return super(AdminRequiredMixin, self).dispatch(request, *args, **kwargs)


class StaffRequiredMixin(object):
    """
    Mixin allows you to require a user with `is_staff` set to True.
    """

    def dispatch(self, request, *args, **kwargs):
        # If the user is a staff user,
        if not request.user.is_staff:
            raise exceptions.AjaxPermissionDeny()
        return super(StaffRequiredMixin, self).dispatch(request, *args, **kwargs)


class PermissionRequiredMixin(object):
    """
    View mixin which verifies that the logged in user has the specified
    permission.

    Class Settings
    `permission_required` - the permission to check for.

    get from https://github.com/brack3t/django-braces/blob/master/braces/views.py
    """
    permission_required = None  # Default required perms to none

    def dispatch(self, request, *args, **kwargs):
        # Make sure that the permission_required attribute is set on the
        # view, or raise a configuration error.
        if self.permission_required is None:
            raise ImproperlyConfigured(
                "'PermissionRequiredMixin' requires "
                "'permission_required' attribute to be set.")

        if not request.user.is_staff:
            raise exceptions.AjaxPermissionDeny()

        # Check to see if the request's user has the required permission.
        has_permission = request.user.is_superuser or request.user.has_perm(self.permission_required)
        # If the user lacks the permission
        if not has_permission:
            raise exceptions.AjaxPermissionDeny()

        return super(PermissionRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class ModelAccessibilityMixin(object):
    def dispatch(self, request, *args, **kwargs):
        base_model = self.get_object()
        # do nothing for the new case which model is none
        if base_model is None:
            return super(ModelAccessibilityMixin, self).dispatch(request, *args, **kwargs)
        if base_model and request.user.has_perm_access(base_model):
            if request.method == "GET" and 'check_access' in request.GET:
                return HttpResponseJson(exceptions.build_success_response_result(), request)
        else:
            raise exceptions.AjaxPermissionDeny()
        return super(ModelAccessibilityMixin, self).dispatch(request, *args, **kwargs)


class RequestAwareMixin(object):
    """
    A mixin to make "request" object available to Form.
    """

    def get_initial(self):
        initial = super(RequestAwareMixin, self).get_initial()
        initial["request"] = self.request
        return initial


class AjaxListView(AjaxLoginRequiredMixin, ListView):
    http_method_names = ['get']
    template_name = 'common/admin/generic.list.inc.html'


class FormProcessMixin(object):

    def form_valid(self, form):
        try:
            self.object = form.save()
        except ValidationError as e:
            form.add_error(None, e.message)
            self.form_invalid(form)
            return

        if hasattr(form, 'save_m2m'):
            try:
                # FIXME: it raise exception if the form is associated many2many with intermediary model
                # ignore it due to caller has done m2m saving.
                form.save_m2m()
            except:
                pass
        response_data = exceptions.build_success_response_result()
        response_data["id"] = self.object.id
        self.post_process(True, response_data)
        return HttpResponseJson(response_data, self.request)

    def form_invalid(self, form):
        self.post_process(False, form.errors)
        raise exceptions.AjaxValidateFormFailed(errors=form.errors)

    def post_process(self, is_success, response_data):
        pass


class ModalShowMixin(object):
    def get_context_data(self, **kwargs):
        context = super(ModalShowMixin, self).get_context_data(**kwargs)
        if self.request.GET.get('modal'):
            context['modal_show'] = True
        return context


class AjaxCreateView(AjaxLoginRequiredMixin, ActionUrlBuilderMixin, ModalShowMixin, FormProcessMixin, CreateView):
    http_method_names = ['get', 'post']
    form_action_url_name = ""
    template_name = 'common/admin/generic.form.inc.html'
    root_namespace = "admin"

    def get(self, request, *args, **kwargs):
        url = self.form_action_url_name or self.get_action_url(self.model, 'create')
        form_action = reverse(url)
        self.object = None
        form = self.get_form(self.get_form_class())
        return self.render_to_response(self.get_context_data(form_action=form_action, form=form))


class AjaxUpdateView(AjaxLoginRequiredMixin, ActionUrlBuilderMixin, ModalShowMixin, FormProcessMixin, UpdateView):
    http_method_names = ['get', 'post']
    form_action_url_name = ""
    template_name = 'common/admin/generic.form.inc.html'
    root_namespace = "admin"

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        url = self.form_action_url_name or self.get_action_url(self.model, 'edit')
        form_action = reverse(url, kwargs={'pk': pk})
        self.object = self.get_object()
        form = self.get_form(self.get_form_class())
        return self.render_to_response(self.get_context_data(form_action=form_action, form=form))


class AjaxFormView(AjaxLoginRequiredMixin, ActionUrlBuilderMixin, ModalShowMixin, FormProcessMixin, UpdateView):
    http_method_names = ['get', 'post']
    form_action_url_name = ""
    template_name = 'common/admin/generic.form.inc.html'
    root_namespace = "admin"
    object = None

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        if int(pk) == 0:
            return None
        return super(AjaxFormView, self).get_object(queryset)

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        self.object = self.get_object()
        form = self.get_form(self.get_form_class())
        return self.render_to_response(self.get_context_data(form_action=self.get_form_action(pk), form=form))

    def get_form_action(self, pk):
        url = self.form_action_url_name or self.get_action_url(self.model, 'edit')
        return reverse(url, kwargs={'pk': pk})


class AjaxFormsetEditView(AjaxLoginRequiredMixin, ModalShowMixin, RequestAwareMixin, ContextMixin, View):
    form_class = None
    formset_class = None
    master_model = None
    model = None
    form_action_url_name = ""
    master_list_url_name = ""
    template_name = 'common/admin/widget-box.formset.inc.html'
    http_method_names = ['get', 'post']
    # must be divide by 12 like 2, 3, 4, 6, 12 for follow the bootstrap span 12
    form_column_count = 3
    nested_model_verbose_name = u''
    master_model_verbose_name = u''

    class BootstrapFormsetHelper(FormHelper):
        form_class = 'form-horizontal'
        form_tag = False
        disable_csrf = True
        render_hidden_fields = True

    def get_formset_initial(self):
        return None

    def get_formset_class(self):
        return self.formset_class

    def get_initial(self):
        return {"request": self.request}

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        return get_object_or_404(self.master_model, id=pk)

    def get(self, request, *args, **kwargs):
        if 12 % self.form_column_count != 0:
            raise BaseException(
                'form_column_count must be divide by 12 like 2, 3, 4, 6, 12 for follow the bootstrap col-md- 12')
        pk = self.kwargs.get('pk')
        if pk and int(pk) != 0:
            master = self.get_object()
        else:
            master = self.master_model()
        return render(request, self.template_name, self.get_context_data(pk=pk, master=master))

    def get_context_data(self, **kwargs):
        context = super(AjaxFormsetEditView, self).get_context_data(**kwargs)
        master = kwargs['master']
        form_action = reverse(self.form_action_url_name, kwargs={'pk': self.kwargs['pk']})
        context.update({
            'form': self.form_class(initial=self.get_initial(), instance=master) if self.form_class else None,
            'formset': self.get_formset_class()(instance=master, initial=self.get_formset_initial(),
                                                prefix=self.model._meta.object_name.lower()),
            'form_action': form_action,
            'model_verbose_name': self.model._meta.verbose_name,
            'master_model_verbose_name': self.master_model_verbose_name,
            'nested_model_verbose_name': self.nested_model_verbose_name,
            'object': master,
            'column_count': self.form_column_count,
            'helper': self.get_form_helper(),
            'form_id': "id_%s_%s_form" % (self.model._meta.object_name, int(time.time()))
        })
        return context

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        if pk and int(pk) != 0:
            master = self.get_object()
        else:
            master = self.master_model()
        form = None
        if self.form_class:
            form = self.form_class(request.POST, request.FILES, initial=self.get_initial(), instance=master)
            if not form.is_valid():
                raise exceptions.AjaxValidateFormFailed(errors=form.errors)

        formset = self.get_formset_class()(request.POST, request.FILES, instance=master,
                                           prefix=self.model._meta.object_name.lower())
        if formset.is_valid():
            with transaction.atomic():
                # XXX: should do form save only if formset is valid.
                if form:
                    form.save()
                for fm in formset:
                    if fm in formset.deleted_forms:
                        obj = fm.instance
                        if obj.id:
                            obj.delete()
                    else:
                        fm.request = request
                        if form:
                            setattr(fm.instance, formset.fk.name, form.instance)
                        fm.save()
                try:
                    formset.save_m2m()
                except:
                    pass
            result = exceptions.build_success_response_result()
        else:
            # wrap the formset errors to a dict which is understand by client.
            counter = 0
            errors = {}
            for section_errors in formset.errors:
                if section_errors:
                    for key, value in section_errors.items():
                        errors[u"%s-%d-%s" % (self.model._meta.object_name.lower(), counter, key)] = value
                counter += 1
            raise exceptions.AjaxValidateFormFailed(errors=errors)
        return HttpResponseJson(result, request)

    def get_form_helper(self):
        return None


class AjaxTableInlineFormsetEditView(AjaxFormsetEditView):
    template_name = 'common/admin/table-inline.formset.inc.html'

    class TableInlineFormSetHelper(FormHelper):
        form_tag = False
        template = 'common/admin/bootstrap3/table_inline_formset.html'

    def get_form_helper(self):
        return AjaxTableInlineFormsetEditView.TableInlineFormSetHelper()


class AjaxNestedFormsetEditView(AjaxTableInlineFormsetEditView):
    template_name = 'common/admin/nested.formset.inc.html'


class AjaxSimpleUpdateView(AjaxLoginRequiredMixin, UpdateView):
    http_method_names = ['get', 'post']

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        message = self.update(obj)
        if message:
            raise exceptions.AjaxValidateFormFailed(errors=message)
        return HttpResponseJson(exceptions.build_success_response_result(), request)

    def update(self, obj):
        return ""

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class AjaxActionView(AjaxSimpleUpdateView):
    def update(self, obj):
        action_method = self.kwargs['action_method']
        msg = getattr(self, action_method)(obj)
        return msg


class ModelAwareBaseMixin(object):
    request = None
    model = None

    def get_context_data(self, **kwargs):
        context = super(ModelAwareBaseMixin, self).get_context_data(**kwargs)
        model_name = self.get_model_name()
        context['model_name'] = model_name
        # noinspection PyProtectedMember
        context['model_verbose_name'] = self.model._meta.verbose_name
        context['form_id'] = "id_%s_%s_form" % (model_name, int(time.time()))
        # keep the current page path. So browser can refresh the page corretly.
        context['page_path'] = self.request.path
        return context

    def get_model_name(self):
        model_name = getattr(self, 'model_name', None)
        if not model_name:
            # noinspection PyProtectedMember
            model_name = self.model._meta.object_name.lower()
        return model_name


class ModelAwareMixin(ModelAwareBaseMixin):
    """
    A mixin to inject some model useful information to context
    So we can make some common template code.
    NOTE: It require below naming conversion
    1. all of url must define a name mixed with namespace
    2. all of model must define a verbose_name
    """

    def get_context_data(self, **kwargs):
        context = super(ModelAwareMixin, self).get_context_data(**kwargs)
        namespace = getattr(self, 'app_label', None)
        if namespace is None:
            # noinspection PyProtectedMember
            namespace = self.model._meta.app_label
        namespace = "%s%s" % (self.get_ns_prefix(), ":" + namespace if namespace else "")
        model_name = self.get_model_name()

        list_url = self.get_list_url()
        context['list_url'] = context.get('list_url', list_url or reverse('%s:%s_list' % (namespace, model_name)))
        context['edit_url'] = context.get('edit_url', '%s:%s_edit' % (namespace, model_name))
        context['delete_url'] = context.get('delete_url', '%s:%s_delete' % (namespace, model_name))
        context['datatables_list_url'] = context.get('datatables_list_url', context['list_url'] + '.json/')
        try:
            if context.get('create_url') is None:
                context['create_url'] = context.get('create_url', reverse('%s:%s_create' % (namespace, model_name)))
        except NoReverseMatch:
            context['create_url'] = context.get('create_url', '')
        return context

    def get_ns_prefix(self):
        return 'admin'

    def get_list_url(self):
        return ''


class ModelDetailView(ActionUrlBuilderMixin, DetailView):
    http_method_names = ['get']
    template_name = 'common/admin/model.detail.inc.html'
    related_sources = []
    root_namespace = "admin"
    object = None

    def get(self, request, *args, **kwargs):
        if hasattr(self, "model_detail_class"):
            model = None
            model_detail_class = self.model_detail_class
        else:
            # use default one if child class doesn't specify "model_detail_class"
            model = self.model
            model_detail_class = ModelDetail

        model_detail = model_detail_class(self.request.user, self.kwargs.get(self.pk_url_kwarg, None), model)
        self.object = model_detail.instance

        builders = []
        for source in self.get_related_sources(self.object):
            model_class = source['modal_class']
            # noinspection PyProtectedMember
            model_meta = model_class._meta
            create_url = source.get('create_url')
            if not create_url:
                create_url = reverse(self.get_action_url(model_class, 'create'))
            builders.append({
                'datatables_builder': source['builder_class'],
                'datatables_list_url': reverse(source['datatable_list_name'], kwargs={'pk': self.object.id}),
                'model_name': model_meta.object_name,
                'model_verbose_name': source.get('model_verbose_name', model_meta.verbose_name),
                'create_url': create_url,
                'modal_show': source.get('modal_show', False)
            })
        return self.render_to_response(self.get_context_data(object=self.object,
                                                             model=model_detail,
                                                             builders=builders,
                                                             page_path=self.request.path))

    def get_related_sources(self, master_model):
        return self.related_sources


class DatatablesSearchMix(object):

    def get_datatables_search_filters(self, datatable_builder, http_query_params):
        searching_filters = {}
        q_list = []
        for (index, field) in enumerate(datatable_builder.fields.values()):
            if not field.is_searchable:
                continue
            search_text = http_query_params.get('columns[%d][search][value]' % index)
            if search_text and search_text != 'null':
                search_expr = field.search_expr
                if not search_expr:
                    field_name = http_query_params.get('columns[%d][data]' % index)
                    # 如果search表达式为空，则用属性名
                    search_expr = field_name
                    if isinstance(field, CharField):
                        # 如果是CharField，则用模糊查询
                        search_expr += '__icontains'
                    elif isinstance(field, ChoiceField):
                        search_expr += '__in'
                        searching_filters[search_expr] = search_text.split(',')
                    searching_filters[search_expr] = searching_filters.get(search_expr) or search_text
                elif hasattr(search_expr, '__iter__'):
                    q = None
                    for expr in search_expr:
                        e = {expr: search_text}
                        if q is None:
                            q = Q(**e)
                        else:
                            q |= Q(**e)
                    q_list.append(q)
                elif callable(search_expr):
                    q_list.append(search_expr(search_text))
                else:
                    searching_filters[search_expr] = searching_filters.get(search_expr) or search_text

        return searching_filters, q_list


class AjaxDatatablesView(AjaxLoginRequiredMixin, DatatablesSearchMix, ListView):
    """
    app search and feed the result to jquery.datatables.
    the search result must match the defintion of jquery.datatables.
    see http://www.datatables.net/release-datatables/examples/data_sources/server_side.html
    """

    http_method_names = ['get', 'post']
    datatables_builder_class = None
    default_sort_field = None
    template_name = 'common/admin/generic.list.inc.html'

    def get_queryset(self):
        if "json" not in self.kwargs:
            return self.model.objects.none()
        return super(AjaxDatatablesView, self).get_queryset()

    def _handle_request(self, request, request_params):
        datatables_builder = self.get_datatables_builder_class()()
        if hasattr(self, 'on_datatables_builder_ready'):
            self.on_datatables_builder_ready(datatables_builder)

        sorting_field = self.default_sort_field
        sorting_direction = 'asc'
        try:
            # 目前只支持单一排序
            sorting_field_index = int(request_params.get('order[0][column]'))
            sorting_field = request_params.get('columns[%d][data]' % sorting_field_index)
            field = datatables_builder.fields[sorting_field]
            if not field.is_sortable:
                sorting_field = None
            else:
                if field.sorting_field:
                    sorting_field = field.sorting_field
            sorting_direction = request_params.get('order[0][dir]')
        except:
            pass
        if sorting_direction == 'desc':
            sorting_field = '-' + sorting_field

        # searching
        searching_dict, q_list = self.get_datatables_search_filters(datatables_builder, request_params)
        start = int(request_params.get('start'))
        if int(request_params.get('length')) < 0:
            end = sys.maxsize
        else:
            end = start + int(request_params.get('length'))

        total, data = self.get_data(sorting_field, start, end, datatables_builder, *q_list, **searching_dict)

        res = {"draw": int(request_params.get('draw')), "recordsTotal": total, "recordsFiltered": total, "data": data}
        request_params = self.on_build_response_data(res)
        return HttpResponseJson(request_params, request)

    def get_data(self, sorting_field, start, end, datatables_builder, *args, **kwargs):
        queryset = self.get_queryset()
        if len(args) or len(kwargs):
            queryset = queryset.filter(*args, **kwargs)
        total = queryset.count()
        if sorting_field:
            queryset = queryset.order_by(sorting_field)
        queryset = self.on_queryset_ready(list(queryset[start:end]))
        data = []
        for index, model_instance in enumerate(queryset):
            data.append(self.get_json_data(index, model_instance, datatables_builder))
        return total, data

    def get(self, request, *args, **kwargs):
        if "json" not in self.kwargs:
            return super(AjaxDatatablesView, self).get(request, *args, **kwargs)

        return self._handle_request(request, request.GET)

    def post(self, request, *args, **kwargs):
        return self._handle_request(request, request.POST)

    def on_queryset_ready(self, queryset):
        """
        a hook to allow inherited class to manipulate the queryset before use
        """
        return queryset

    def on_build_response_data(self, data):
        """
        a hook to allow inherited class to override the response data
        """
        return data

    def get_json_data(self, index, model_instance, datatables_builder):
        data = OrderedDict()
        for name, builder_field in datatables_builder.fields.items():
            render = getattr(builder_field, 'render')
            if callable(render):
                val = render(self.request, model_instance, name)
            else:
                val = render.render(self.request, model_instance, name)
                # XXX: escape the content to avoid "javascript inject issue"
                val = escape(val)
            data[name] = val
            if hasattr(model_instance, 'id'):
                data['DT_RowId'] = "row_%s" % model_instance.id
            data['DT_RowData'] = {"index": index}
        return data

    def get_datatables_builder_class(self):
        return self.datatables_builder_class


class DatatablesBuilderMixin(object):

    def get_context_data(self, **kwargs):
        data = super(DatatablesBuilderMixin, self).get_context_data(**kwargs)
        datatables_builder_class = self.get_datatables_builder_class()
        data['datatables_builder'] = datatables_builder_class()
        self.on_datatables_builder_ready(data['datatables_builder'])
        datatables_list_url = self.get_datatables_list_url()
        if datatables_list_url:
            data['datatables_list_url'] = datatables_list_url
        # 每个datatables都应该有唯一的prefix,即使它们拥有是相同的model.
        data['datatables_id_prefix'] = self.get_datatables_id_prefix()
        return data

    def get_datatables_list_url(self):
        return ''

    def get_datatables_id_prefix(self):
        return self.__class__.__name__

    def on_datatables_builder_ready(self, builder):
        pass


class ExcelBuilderMixIn(object):
    def write_row_data(self, sheet, row, data):
        sheet.write_row(row, 0, data, self.content_format)

    def get_row_data(self, model, form):
        ret = []
        for form_field in form:
            try:
                model_field = form._meta.model._meta.get_field(form_field.name)
            except FieldDoesNotExist as e:
                # raise the field not defined in form to subclass
                val = self.handle_unknown_field(model, form_field.name)
            else:
                # print model_field.attname, model_field.get_attname(), '=', getattr(obj, model_field.attname)
                val = model_field.value_to_string(model)
                if isinstance(model_field, RelatedField):
                    if form_field.name == 'owner':
                        try:
                            val = model.owner.get_full_name() if model.owner else u""
                        except:
                            val = u''
                    elif form_field.name == 'creator':
                        val = model.creator.get_full_name() if model.creator else u""
                    else:
                        val = self.handle_related_field(model, val, form_field.name, model_field)
                elif isinstance(model_field, d_fields.DateField) or isinstance(model_field, d_fields.DateTimeField):
                    date = getattr(model, model_field.attname, None)
                    if date:
                        val = local_time_to_text(date)
                elif isinstance(model_field, d_fields.IntegerField):
                    if val is None or val == u'None':
                        val = 0
                    val = int(val)
                    if model_field.choices:
                        display_method = getattr(model, 'get_%s_display' % model_field.attname, None)
                        if display_method:
                            display = display_method()
                            if display:
                                val = display
            ret.append(val)
        return ret

    def handle_unknown_field(self, model, field_name):
        logger.debug("handle_unknown_field %s:%s" % (model, field_name))
        return ""

    def handle_related_field(self, model, field_value, field_name, field):
        logger.debug("handle_related_field " + field_name + "  " + field_value)
        return field_value

    def build_excel(self, excel_form, col_width={}):
        _content_format = {
            'font_size': 11,
            'font_name': u'微软雅黑',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        }
        output = StringIO()
        book = Workbook(output, {'in_memory': True})
        self.content_format = book.add_format(_content_format)

        sheet = book.add_worksheet(u'数据')
        sheet.set_default_row(24)
        sheet.freeze_panes(1, 0)

        for i, field in enumerate(excel_form):
            # xlsxwriter中列宽用字符数表示，xlws中列宽用字符数*256表示，需要折算，256为字符衡量单位
            initial_width = col_width.get(field.name) or 15
            width = (initial_width / 256) if initial_width > 100 else initial_width
            sheet.set_column(i, i, width)

        sheet.set_column(0, 100, 40)

        # write header
        header = [u"%s" % field.label for field in excel_form]
        self.write_row_data(sheet, 0, header)

        # write content
        for row_index, model in enumerate(self.get_queryset(), start=1):
            self.write_row_data(sheet, row_index, self.get_row_data(model, excel_form))

        book.close()
        output.seek(0)
        return output.read()


class ExcelExportView(ExcelBuilderMixIn, ListView):
    http_method_names = ['get']
    excel_file_name = u'数据'
    model_form_class = None
    col_width = {}

    def get_initial(self):
        return {"request": self.request}

    def get(self, request, *args, **kwargs):
        form = self.model_form_class()
        content = self.build_excel(form, self.col_width)
        # mime type for excel: http://stackoverflow.com/questions/974079/setting-mime-type-for-excel-document
        response = HttpResponse(content,
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        excel_file_name = self.get_excel_file_name().encode('utf-8')
        if 'HTTP_USER_AGENT' in request.META:
            # for more details see http://greenbytes.de/tech/tc2231/
            if u'WebKit' in request.META['HTTP_USER_AGENT']:
                # Safari 3.0 and Chrome 2.0 accepts UTF-8 encoded string directly.
                filename_in_header = 'filename=%s' % excel_file_name
            elif u'MSIE' in request.META['HTTP_USER_AGENT']:
                # IE does not support internationalized filename at all.
                filename_in_header = 'download.xls'
            else:
                # For others like Firefox, we follow RFC2231 (encoding extension in HTTP headers).
                filename_in_header = 'filename*=UTF-8\'\'%s' % urllib.quote(excel_file_name)
        else:
            filename_in_header = 'filename*=UTF-8\'\'%s' % urllib.quote(excel_file_name)

        response['Content-Disposition'] = 'attachment; %s' % filename_in_header
        response['Cache-Control'] = 'no-cache'
        return response

    def get_excel_file_name(self):
        return "%s-%s.xls" % (self.excel_file_name, datetime.datetime.now().strftime("%Y%m%d%H%M"))


class NavigationHomeMixin(object):
    def get_context_data(self, **kwargs):
        context = super(NavigationHomeMixin, self).get_context_data(**kwargs)
        context['hide_back_btn'] = True
        return context


class ModelActiveView(AjaxSimpleUpdateView):
    """
    Only work for one string field.
    Use 'unique_field_on_inactive' to defined field name if it's not the 'name'.
    """
    unique_field_on_inactive = 'name'

    def update(self, obj):
        obj.is_active = not obj.is_active
        if not obj.is_active:
            field = obj.__class__._meta.get_field(self.unique_field_on_inactive)
            if field:
                field_attr = getattr(obj, self.unique_field_on_inactive)
                id_attr = str(getattr(obj, 'id'))
                if field_attr and field and field.unique:
                    new_val = ('%s-%s' % (id_attr, field_attr))[0:field.max_length]
                    setattr(obj, self.unique_field_on_inactive, new_val)
        obj.save()


class AjaxDetailView(AjaxLoginRequiredMixin, DetailView):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(object=self.object))


class HttpResponseJson(HttpResponse):
    def __init__(self, result, request=None, **extra):
        content_type = 'application/json; charset=utf-8'
        if request:
            # e.g.
            # Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)
            ua = request.META['HTTP_USER_AGENT']
            if ua and (ua.find('MSIE 8') != -1 or ua.find('MSIE 9') != -1):
                content_type = 'text/plain; charset=utf-8'

        super(HttpResponseJson, self).__init__(
            content=json.dumps(result, ensure_ascii=False),
            content_type=content_type, **extra)


class CsrfExemptMixin(object):
    """
    Exempts the view from CSRF requirements.

        NOTE: This should be the left-most mixin of a view.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CsrfExemptMixin, self).dispatch(*args, **kwargs)


class ModelCheckAccessMixin(object):
    request = None

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        if self.request.method == 'GET' and 'check_access' in self.request.GET:
            error_msg = self.check_access(self.request)
            if error_msg:
                data = {"ret": -1, "errmsg": error_msg}
            else:
                data = exceptions.build_success_response_result()
            return HttpResponseJson(data, self.request)

        return super(ModelCheckAccessMixin, self).dispatch(*args, **kwargs)

    def check_access(self, request):
        """
        return empty string or None to indicate the checking is success.
        """
        return ""
