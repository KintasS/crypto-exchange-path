from crypto_exchange_path.models import Coin, TradePair, Fee, Price, Exchange
from crypto_exchange_path import db
from crypto_exchange_path.config import Params


def get_active_coins(type=None, price_id=False):
    """Returns the complete list of active coins available in 'Coin' table.
    By default, it returns its symbols, unless 'price_id' is set to True.
    If type is given, only those coins are retrieved (Cryptos o Fiat)
    """
    if type:
        coin_in_db = Coin.query.filter_by(type=type, status="Active").all()
    else:
        coin_in_db = Coin.query.filter_by(status="Active").all()
    coin_list = []
    if price_id:
        for coin in coin_in_db:
            coin_list.append(coin.price_id)
    else:
        for coin in coin_in_db:
            coin_list.append(coin.id)
    return coin_list


def get_coin(id):
    """Returns a Coin object given its symbol.
    """
    coin = Coin.query.filter_by(id=id.upper()).first()
    return coin


def get_coin_by_longname(longname):
    """Returns a Coin object given its longname.
    """
    coin = Coin.query.filter_by(long_name=longname).first()
    return coin


def get_coin_by_price_id(price_id):
    """Returns a Coin object given its 'price_id'.
    """
    coin = Coin.query.filter_by(price_id=price_id).first()
    return coin


def get_exchange(id):
    """Returns the exchange object with the given 'id'.
    """
    exchange = Exchange.query.filter_by(id=id).first()
    if exchange:
        return exchange
    else:
        return None


def get_exchanges(type=None):
    """Returns the list of exchanges available in 'Exchange' table.
    """
    if type:
        exchanges = Exchange.query.filter_by(type=type).all()
    else:
        exchanges = Exchange.query.all()
    if exchanges:
        exchanges = [exch.id for exch in exchanges]
        return sorted(exchanges)


def get_exchange_choices(types=[]):
    """Returns the list of exchanges available in 'Exchange' table,
    but in tuples so that it works with Input form choices.
    """
    exchanges = []
    for type in types:
        exchanges += Exchange.query.filter_by(type=type).all()
    choices = []
    for exch in exchanges:
        choices.append((exch.id, exch.name))
    return choices


def get_feedback_topics():
    """Gets the feedback topics from the configuration file and builds
    a list of tuples.
    """
    topics = Params.FEEDBACK_TOPICS
    choices = [('(Select a topic)', '(Select a topic)')]
    for topic in topics:
        choices.append((topic, topic))
    return choices


def get_currency_choices():
    """Returns the list of currencies available in 'Exchange' table,
    but in tuples so that it works with Input form choices.
    """
    currencies = get_active_coins('Fiat')
    choices = []
    for currency in currencies:
        choices.append((currency, currency))
    return choices


def get_exch_by_pair(coin, base_coin, logger):
    """Gets the exchanges that trade a given pair,
    together with its Volume_24h.
    Results are sorted by Volume_24h.
    """
    exchs = db.session.query(TradePair)\
                      .filter(((TradePair.coin == coin) &
                               (TradePair.base_coin == base_coin)) |
                              ((TradePair.coin == base_coin) &
                               (TradePair.base_coin == coin)))\
                      .order_by(TradePair.volume.desc()).all()
    logger.debug("get_exch_by_pair: Returned '{}'exchanges that "
                 "trade '{}-{}'".format(len(exchs), coin, base_coin))
    if exchs:
        return set([item.exchange for item in exchs])
    return set()


def get_exch_by_coin(coin):
    """Gets the exchanges that allows deposit or withdrawal of 'coin'.
    It is assumed that, in order for an exchange to allow the deposit of a
    coin, it must allow the withdrawal of that coin (which should be the case).
    """
    exchs = db.session.query(Fee.exchange)\
                      .filter((Fee.action == 'Withdrawal') &
                              (Fee.scope == coin))\
                      .distinct(Fee.exchange).all()
    if exchs:
        return set([item[0] for item in exchs])
    return set()


def calc_fee(action, exchange, coin, amt, logger):
    """Gets the deposit or withdrawal fee of 'exchange'/'coin'.
    Returns: [<fee_amt>, <fee_details>]
    """
    fee_query = Fee.query.filter_by(exchange=exchange,
                                    action=action,
                                    scope=coin).first()
    if fee_query:
        # If Type == 'Absolute', just return value
        if fee_query.type == 'Absolute':
            lit = "{} {} (fixed amount)".format(fee_query.amount,
                                                coin)
            return [fee_query.amount, lit]
        # If Type == 'Percentage', calc fee and check minimum quantity
        elif fee_query.type == 'Percentage':
            wd_fee = fee_query.amount / 100 * amt
            if fee_query.min_amount:
                lit = "{}% (minimum fee of {} {})"\
                    .format(fee_query.amount,
                            fee_query.min_amount,
                            coin)
                return [max(wd_fee, fee_query.min_amount), lit]
            else:
                lit = "{}%".format(fee_query.amount)
                return [wd_fee, lit]
        # If Type == 'IfLess1kUSD', get amount in USD and check if less than 1k
        elif fee_query.type == 'IfLess1kUSD':
            amount_usd = fx_exchange(coin, 'USD', amt, logger)
            if amount_usd < 1000:
                lit = "{} {} (fixed amount for deposits of less than $1000)"\
                    .format(fee_query.amount, coin)
                return [fee_query.amount, lit]
        # If Type == '1%+20', calc 1% and then add 20 units
        elif fee_query.type == '1%+20':
            wd_fee = round(0.01 * amt + 20, 2)
            lit = "1% + 20 {}".format(coin)
            return [wd_fee, lit]
    return [None, None]


def is_crypto(crypto):
    """Checks whether a coin is a crypto(True) or a fiat coin(False).
    """
    coin = Coin.query.filter_by(id=crypto).first()
    if coin and coin.type == 'Crypto':
        return True
    else:
        return False


def fx_exchange(orig_coin, dest_coin, amount, logger):
    if amount is None:
        logger.warning("fx_exchange: FX could not be calculated for '{}"
                       "-{}' (amount=None)".format(orig_coin, dest_coin))
        return None
    # If 'orig_coin'='dest_coin', return 'amount' directly
    if orig_coin == dest_coin:
        return amount
    # If Price is found & 'dest_coin' is a 'base_coin', return price
    prc = Price.query.filter_by(coin=orig_coin, base_coin=dest_coin)\
                     .first()
    if prc:
        return round(prc.price * amount, 8)
    # If Price is found & 'dest_coin' is a 'coin', return 1/price
    prc = Price.query.filter_by(coin=dest_coin, base_coin=orig_coin)\
                     .first()
    if prc:
        return round(1 / prc.price * amount, 8)
    # Else, triangulate FX using BTC prices (Case if Type=Crypto)
    prc_orig_btc = Price.query.filter_by(coin=orig_coin, base_coin='BTC')\
                              .first()
    prc_dest_btc = Price.query.filter_by(coin=dest_coin, base_coin='BTC')\
                              .first()
    if prc_orig_btc and prc_dest_btc:
        return round(prc_orig_btc.price / prc_dest_btc.price * amount, 8)
    # Else, triangulate FX using BTC prices (Case if Type=Fiat)
    prc_orig_fiat = Price.query.filter_by(coin='BTC', base_coin=orig_coin)\
        .first()
    prc_dest_fiat = Price.query.filter_by(coin='BTC', base_coin=dest_coin)\
        .first()
    if prc_orig_fiat and prc_dest_fiat:
        return round(prc_dest_fiat.price / prc_orig_fiat.price * amount, 8)
    # If the FX could not be calculated, return 'None'
    logger.warning("fx_exchange: FX could not be calculated for '{}"
                   "-{}'".format(orig_coin, dest_coin))
    return None
