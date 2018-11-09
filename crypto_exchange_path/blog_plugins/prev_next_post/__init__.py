from flask_blogging import signals
from flask_blogging.sqlastorage import SQLAStorage
import sqlalchemy as sqla
from slugify import slugify
from sqlalchemy import func


def get_prev_post(sqla_storage, post):
    """ Gets the previous post.
    """
    if post:
        prev_id = post['post_id'] - 1
        engine = sqla_storage.engine
        with engine.begin() as conn:
            post_table = sqla_storage.post_table
            while prev_id > 0:
                statement = sqla.select([post_table]) \
                    .where(post_table.c.id == prev_id)
                result = conn.execute(statement).fetchone()
                if result:
                    prev_post = sqla_storage.get_post_by_id(prev_id)
                    if prev_post:
                        slug = slugify(prev_post['title'])
                        prev_post['Slug'] = slug
                        return prev_post
                prev_id -= 1
    return None


def get_next_post(sqla_storage, post):
    """ Gets the next post.
    """
    if post:
        next_id = post['post_id'] + 1
        engine = sqla_storage.engine
        with engine.begin() as conn:
            post_table = sqla_storage.post_table
            statement = sqla.select([func.max(post_table.c.id)])
            max_post_id = conn.execute(statement).fetchone()
            if max_post_id:
                max_post_id = max_post_id[0]
            while next_id <= max_post_id:
                statement = sqla.select([post_table]) \
                    .where(post_table.c.id == next_id)
                result = conn.execute(statement).fetchone()
                if result:
                    next_post = sqla_storage.get_post_by_id(next_id)
                    if next_post:
                        slug = slugify(next_post['title'])
                        next_post['Slug'] = slug
                        return next_post
                next_id += 1
    return None


def get_surrounding_posts(app, engine, post, meta):
    """ Generation of additional meta tags for the 'post' page:
          - meta.prev_post --> Previous post object (+slug)
          - meta.next_post --> Previous post object (+slug)
    """
    if isinstance(engine.storage, SQLAStorage):
        # Get previous post
        prev_post = get_prev_post(engine.storage, post)
        meta["prev_post"] = prev_post
        # Get next post
        next_post = get_next_post(engine.storage, post)
        meta["next_post"] = next_post
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def register(app):
    signals.page_by_id_fetched.connect(get_surrounding_posts)
    return
