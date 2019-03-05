from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_admin import Admin
from flask_security import Security, SQLAlchemyUserDatastore
from flask_admin import helpers as admin_helpers
from flask_blogging import SQLAStorage, BloggingEngine
from crypto_exchange_path.config import AppConfig
from crypto_exchange_path.admin_view import (ExchangeView,
                                             FeeView,
                                             CoinView,
                                             TradePairView,
                                             MappingsView,
                                             SubscriberView,
                                             PriceView,
                                             FeedbackView,
                                             QueryRegisterView,
                                             UserView,
                                             RoleView,
                                             PostView,
                                             TagView)

app = Flask(__name__)
app.config.from_object(AppConfig)
db = SQLAlchemy(app)
mail = Mail(app)

# Create Flask Admin
admin = Admin(app, name='CFS Admin',
              url='/cfs_admin',
              base_template='admin_base.html',
              template_mode='bootstrap3')


from crypto_exchange_path import routes
from crypto_exchange_path.models import (User, Role, Exchange, Fee, Coin,
                                         TradePair, Mappings, Subscriber,
                                         Price, Feedback,
                                         QueryRegister)

# Create Blogging
with app.app_context():
    sql_storage = SQLAStorage(db=db)
    blog_engine = BloggingEngine(app, sql_storage)
from flask_blogging.sqlastorage import Post, Tag  # Has to be after SQLAStorage initialization


@blog_engine.user_loader
def load_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    return user


# Create Admin views
admin.add_view(ExchangeView(Exchange, db.session, category="Site Data"))
admin.add_view(FeeView(Fee, db.session, category="Site Data"))
admin.add_view(CoinView(Coin, db.session, category="Site Data"))
admin.add_view(TradePairView(TradePair, db.session, category="Site Data"))
admin.add_view(MappingsView(Mappings, db.session, category="Site Data"))
admin.add_view(PriceView(Price, db.session, category="Site Data"))
admin.add_view(SubscriberView(Subscriber, db.session))
admin.add_view(UserView(User, db.session, category="User Config"))
admin.add_view(RoleView(Role, db.session, category="User Config"))
admin.add_view(FeedbackView(Feedback, db.session))
admin.add_view(QueryRegisterView(QueryRegister, db.session))
# Post = sql_storage.post_model
# Tag = sql_storage.tag_model
admin.add_view(PostView(Post, db.session))
admin.add_view(TagView(Tag, db.session))


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


@security.context_processor
def security_context_processor():
    """
    Define a context processor for merging flask-admin's template context into
    the flask-security views.
    """
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )
