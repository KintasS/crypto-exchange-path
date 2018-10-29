from flask_blogging import signals
from flask_blogging.sqlastorage import SQLAStorage


def get_author(app, engine, posts, meta):
    if isinstance(engine.storage, SQLAStorage):
        if posts:
            post = posts[0]
            author = post['user_name']
        meta["author"] = author
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def register(app):
    signals.posts_by_author_processed.connect(get_author)
    return
