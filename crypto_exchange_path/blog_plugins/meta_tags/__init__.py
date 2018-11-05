from flask_blogging import signals
from flask_blogging.sqlastorage import SQLAStorage
from crypto_exchange_path.utils import get_meta_tags


def get_author_meta(app, engine, posts, meta):
    if isinstance(engine.storage, SQLAStorage):
        # Get Author name
        if posts:
            post = posts[0]
            author = post['user_name']
        meta["author"] = author
        # Get page Title & Description
        meta["blog_title"] = get_meta_tags('Blog|Author',
                                           'Title',
                                           [author])
        meta["blog_description"] = get_meta_tags('Blog|Author',
                                                 'Description',
                                                 [author])
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def get_tag_meta(app, engine, posts, meta):
    if isinstance(engine.storage, SQLAStorage):
        # Get page Title & Description
        meta["blog_title"] = get_meta_tags('Blog|Tag',
                                           'Title',
                                           [meta["tag"].upper()])
        meta["blog_description"] = get_meta_tags('Blog|Tag',
                                                 'Description',
                                                 [meta["tag"].upper()])
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def get_index_meta(app, engine, posts, meta):
    if isinstance(engine.storage, SQLAStorage):
        # Get page Title & Description
        meta["blog_title"] = get_meta_tags('Blog',
                                           'Title')
        meta["blog_description"] = get_meta_tags('Blog',
                                                 'Description')
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def get_page_meta(app, engine, post, meta):
    if isinstance(engine.storage, SQLAStorage):
        # Get page Title & Description
        print(post)
        meta["blog_title"] = get_meta_tags('Blog|Page',
                                           'Title',
                                           [post['title']])
        if 'meta' in post.keys():
            if 'summary' in post['meta'].keys():
                if post['meta']['summary']:
                    meta["blog_description"] = get_meta_tags('Blog|Page',
                                                             'Description',
                                                             [post['meta']['summary'][0]])
    else:
        raise RuntimeError("Plugin only supports SQLAStorage. Given storage"
                           "not supported")
    return


def register(app):
    signals.posts_by_author_processed.connect(get_author_meta)
    signals.posts_by_tag_processed.connect(get_tag_meta)
    signals.index_posts_processed.connect(get_index_meta)
    signals.page_by_id_processed.connect(get_page_meta)
    return
