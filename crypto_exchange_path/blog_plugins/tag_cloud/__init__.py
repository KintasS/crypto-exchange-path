from flask_blogging import signals
from flask_blogging.sqlastorage import SQLAStorage
import sqlalchemy as sqla
from slugify import slugify
from sqlalchemy import func


def get_tag_data(sqla_storage):
    """ Gets a list of tags and its occurrences.
    """
    engine = sqla_storage.engine
    with engine.begin() as conn:
        tag_posts_table = sqla_storage.tag_posts_table
        tag_table = sqla_storage.tag_table

        tag_cloud_stmt = sqla.select([
            tag_table.c.text, func.count(tag_posts_table.c.tag_id)]).group_by(
            tag_posts_table.c.tag_id
        ).where(tag_table.c.id == tag_posts_table.c.tag_id)
        tag_cloud = conn.execute(tag_cloud_stmt).fetchall()
    return tag_cloud


def get_tag_cloud_post(app, engine, post, meta):
    """ Generation of additional meta tags for the 'post' page:
          - meta.tag_cloud --> Contains a list of tags and its occurrences.
    """
    if isinstance(engine.storage, SQLAStorage):
        # Get tags
        tag_cloud = get_tag_data(engine.storage)
        meta["tag_cloud"] = tag_cloud
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def get_tag_cloud_index(app, engine, posts, meta):
    if isinstance(engine.storage, SQLAStorage):
        tag_cloud = get_tag_data(engine.storage)
        meta["tag_cloud"] = tag_cloud
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def register(app):
    signals.index_posts_fetched.connect(get_tag_cloud_index)
    signals.page_by_id_fetched.connect(get_tag_cloud_post)
    return
