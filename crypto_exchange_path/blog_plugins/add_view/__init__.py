from flask_blogging import signals
from flask_blogging.views import page_by_id


def add_custom_view(app, engine, blueprint):
    """
    Make post available from URL without 'page"
    """
    blueprint.add_url_rule("/<post_id>/<slug>/",
                           view_func=page_by_id)


def register(app):
    signals.blueprint_created.connect(add_custom_view)
