from flask_blogging import signals
from flask_blogging.sqlastorage import SQLAStorage
from crypto_exchange_path.forms import FeedbackForm


def get_feedback_modal_index(app, engine, posts, meta):
    if isinstance(engine.storage, SQLAStorage):
        feedback_form = FeedbackForm()
        meta["feedback_form"] = feedback_form
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def get_feedback_modal_post(app, engine, post, meta):
    if isinstance(engine.storage, SQLAStorage):
        feedback_form = FeedbackForm()
        meta["feedback_form"] = feedback_form
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def register(app):
    signals.page_by_id_fetched.connect(get_feedback_modal_post)
    signals.index_posts_fetched.connect(get_feedback_modal_index)
    signals.posts_by_tag_fetched.connect(get_feedback_modal_index)
    signals.posts_by_author_fetched.connect(get_feedback_modal_index)
    # signals.feed_posts_fetched.connect(get_feedback_modal_index)
    return
