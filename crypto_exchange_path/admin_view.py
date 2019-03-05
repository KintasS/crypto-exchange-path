from flask import url_for, redirect, request, abort
from flask_admin.contrib.sqla import ModelView
from flask_security import current_user


class MyModelView(ModelView):

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        if current_user.has_role('superuser'):
            return True
        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when
        a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))


class ExchangeView(MyModelView):
    can_create = True
    can_delete = False  # disable model deletion
    edit_modal = True
    page_size = 100  # the number of entries to display on the list view
    column_searchable_list = ['name', 'type']
    column_filters = ['id', 'name', 'type', 'language']
    can_export = True
    column_display_pk = True
    form_columns = ('id', 'name', 'type', 'img_fn', 'site_url',
                    'affiliate', 'language', 'status')


class FeeView(MyModelView):
    can_create = True
    can_delete = True
    edit_modal = True
    page_size = 100  # the number of entries to display on the list view
    column_searchable_list = ['exchange', 'action', 'scope']
    column_filters = ['exchange', 'action', 'scope', 'amount', 'min_amount',
                      'fee_coin', 'type']
    can_export = True
    column_display_pk = True
    column_hide_backrefs = False
    column_list = ('exchange', 'action', 'scope', 'amount', 'min_amount',
                   'fee_coin', 'type')
    form_columns = column_list


class CoinView(MyModelView):
    can_create = True
    can_delete = True
    edit_modal = True
    page_size = 100  # the number of entries to display on the list view
    column_searchable_list = ['id', 'symbol', 'long_name']
    column_filters = ['id', 'symbol', 'long_name', 'type', 'status']
    can_export = True
    column_display_pk = True


class TradePairView(MyModelView):
    can_create = True
    can_delete = True  # disable model deletion
    edit_modal = True
    page_size = 100  # the number of entries to display on the list view
    column_searchable_list = ['exchange', 'coin', 'base_coin']
    column_filters = ['exchange', 'coin', 'base_coin']
    can_export = True
    column_display_pk = True
    column_hide_backrefs = False
    column_list = ('exchange', 'coin', 'base_coin', 'volume')
    form_columns = column_list


class MappingsView(MyModelView):
    can_create = True
    can_delete = True
    edit_modal = True
    page_size = 100  # the number of entries to display on the list view
    column_searchable_list = ['table', 'field', 'old_value', 'new_value']
    column_filters = ['table', 'field', 'old_value', 'new_value']
    can_export = True
    column_display_pk = True


class SubscriberView(MyModelView):
    can_create = True
    can_delete = True
    edit_modal = True
    page_size = 100  # the number of entries to display on the list view
    column_searchable_list = ['email', 'subscription', 'date', 'status']
    column_filters = ['email', 'subscription', 'date', 'status']
    can_export = True
    column_display_pk = True


class PriceView(MyModelView):
    can_create = False
    can_delete = False  # disable model deletion
    edit_modal = True
    page_size = 100  # the number of entries to display on the list view
    column_searchable_list = ['coin', 'base_coin']
    column_filters = ['coin', 'base_coin']
    can_export = True
    column_display_pk = True


class FeedbackView(MyModelView):
    can_create = False
    can_delete = True  # disable model deletion
    edit_modal = True
    page_size = 100  # the number of entries to display on the list view
    column_searchable_list = ['datetime', 'text', 'page', 'status']
    column_filters = ['datetime', 'text', 'page', 'status']
    can_export = True
    column_display_pk = True


class QueryRegisterView(MyModelView):
    can_create = False
    can_edit = False
    can_delete = True  # disable model deletion
    edit_modal = True
    page_size = 20  # the number of entries to display on the list view
    column_filters = ['session_id', 'orig_amt', 'orig_coin', 'orig_loc',
                      'dest_coin', 'dest_loc', 'currency', 'connection_type',
                      'exchanges', 'results', 'start_time', 'finish_time']
    can_export = True
    column_display_pk = True
    column_list = ('id', 'session_id', 'start_time', 'orig_amt', 'orig_coin',
                   'orig_loc', 'dest_coin', 'dest_loc', 'currency',
                   'connection_type', 'results', 'finish_time', 'exchanges')


class UserView(MyModelView):
    can_create = False
    can_delete = False
    can_edit = False
    column_exclude_list = ['password']
    page_size = 10
    column_display_pk = True


class RoleView(MyModelView):
    can_create = False
    can_delete = False
    can_edit = False
    page_size = 10
    column_display_pk = True


class PostView(MyModelView):
    can_create = True
    can_delete = True
    can_edit = True
    page_size = 20
    column_display_pk = True


class TagView(MyModelView):
    can_create = True
    can_delete = True
    can_edit = True
    page_size = 20
    column_display_pk = True
