from flask_security import UserMixin, RoleMixin
from crypto_exchange_path import db


# Define models
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __str__(self):
        return self.email

    def get_name(self):
        return self.username


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    topic = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(50))
    detail = db.Column(db.String(200))

    def __repr__(self):
        date = self.datetime.strftime("%Y%m%d")
        return ("Feedback({} [{}]: {})"
                .format(date, self.topic, self.subject))


class Price(db.Model):
    coin = db.Column(db.String(10), primary_key=True, nullable=False)
    base_coin = db.Column(db.String(10), primary_key=True, nullable=False)
    price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return ("Price({}/{} ({}): {})"
                .format(self.coin, self.currency, self.price))


class Coin(db.Model):
    id = db.Column(db.String(10), primary_key=True, nullable=False)
    symbol = db.Column(db.String(10), unique=True, nullable=False)
    long_name = db.Column(db.String(50), unique=True, nullable=False)
    url_name = db.Column(db.String(50), unique=True, nullable=False)
    price_id = db.Column(db.String(10), unique=True, nullable=False)
    paprika_id = db.Column(db.String(50))
    ranking = db.Column(db.Float)
    image_url = db.Column(db.String(100))
    local_fn = db.Column(db.String(100))
    type = db.Column(db.String(30))
    status = db.Column(db.String(10))

    def __repr__(self):
        return ("Coin({} [{}]: symbol={} price_id={} type={} status={})"
                .format(self.id,
                        self.long_name,
                        self.symbol,
                        self.price_id,
                        self.type,
                        self.status))


class Exchange(db.Model):
    id = db.Column(db.String(30), primary_key=True, nullable=False)
    name = db.Column(db.String(30), unique=True, nullable=False)
    type = db.Column(db.String(30), nullable=False)
    img_fn = db.Column(db.String(50))
    site_url = db.Column(db.String(100))
    affiliate = db.Column(db.String(10), nullable=False)
    language = db.Column(db.String(50))
    trade_pairs = db.relationship('TradePair', backref='exchange_trade',
                                  lazy=True)
    fees = db.relationship('Fee', backref='exchange_fee', lazy=True)

    def __repr__(self):
        return ("Exchange({} [{}])".format(self.name, self.type))


class Fee(db.Model):
    exchange = db.Column(db.String(30), db.ForeignKey('exchange.id'),
                         primary_key=True, nullable=False)
    action = db.Column(db.String(30), primary_key=True, nullable=False)
    scope = db.Column(db.String(30), primary_key=True, nullable=False)
    amount = db.Column(db.Float)
    min_amount = db.Column(db.Float)
    fee_coin = db.Column(db.String(10))
    type = db.Column(db.String(10))

    def __repr__(self):
        return ("Fee({}-{}-{}: {})".format(self.exchange, self.action,
                                           self.scope, self.amount))


class TradePair(db.Model):
    exchange = db.Column(db.String(30), db.ForeignKey('exchange.id'),
                         primary_key=True, nullable=False)
    coin = db.Column(db.String(10), db.ForeignKey('coin.id'),
                     primary_key=True, nullable=False)
    base_coin = db.Column(db.String(10), db.ForeignKey('coin.id'),
                          primary_key=True, nullable=False)
    volume = db.Column(db.Float)

    def __repr__(self):
        return ("TradePair({} [{}/{}]: volume={})".format(self.exchange,
                                                          self.coin,
                                                          self.base_coin,
                                                          self.volume))


class QueryRegister(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    orig_amt = db.Column(db.Float)
    orig_coin = db.Column(db.String(10))
    orig_loc = db.Column(db.String(30))
    dest_coin = db.Column(db.String(10))
    dest_loc = db.Column(db.String(30))
    currency = db.Column(db.String(10))
    connection_type = db.Column(db.Integer)
    exchanges = db.Column(db.String(400))
    results = db.Column(db.Integer)
    start_time = db.Column(db.DateTime)
    finish_time = db.Column(db.DateTime)

    def __repr__(self):
        return ("QueryRegister([{}] id={}, results={})".format(self.session_id,
                                                               self.id,
                                                               self.results))

# class Post(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(256))
#     text = db.Column(db.Text)
#     img_fn = db.Column(db.String(100))
#     post_date = db.Column(db.DateTime)
#     last_modified_date = db.Column(db.DateTime)
#     draft = db.Column(db.SmallInteger)
#
#     def __repr__(self):
#         return ("Post(id={}, title={})".format(self.id,
#                                                self.title))
