from crypto_exchange_path.models import Coin, TradePair, Fee, Price, Exchange
from crypto_exchange_path import db
from crypto_exchange_path.config import Params


def get_active_coins(type=None):
    """Returns the complete list of active coins available in 'Coin' table.
    If type is given, only those coins are retrieved (Cryptos o Fiat)
    """
    if type:
        coin_in_db = Coin.query.filter_by(type=type, status="Active").all()
    else:
        coin_in_db = Coin.query.filter_by(status="Active").all()
    coin_list = []
    for coin in coin_in_db:
        coin_list.append(coin.id)
    return coin_list


def get_coin(id):
    """Returns a Coin object given its symbol.
    """
    coin = Coin.query.filter_by(id=id).first()
    return coin


def get_coin_by_longname(longname):
    """Returns a Coin object given its longname.
    """
    coin = Coin.query.filter_by(long_name=longname).first()
    return coin


def round_amount(amount, coin):
    """Returns a rounded amount depending on the valuation of the coin.
    """
    if not amount:
        return "-"
    if coin in Params.FIAT_COINS:
        try:
            decs = Params.STEPS_DECIMAL_POS[coin]
            return round(amount, decs)
        except Exception as e:
            return amount
    else:
        price = Price.query.filter_by(coin=coin, base_coin='EUR').first()
        if price:
            price = price.price
            if price > 10000:
                decs = 8
            elif price > 1000:
                decs = 7
            elif price > 100:
                decs = 6
            elif price > 10:
                decs = 5
            elif price > 1:
                decs = 4
            elif price > 0.1:
                decs = 3
            elif price > 0.01:
                decs = 2
            elif price > 0.001:
                decs = 1
            else:
                decs = 0
            return "{:20,.{}f}".format(round(amount, decs), decs)
        return amount


def get_exchange(id):
    """Returns the exchange object with the given 'name'.
    If it was not found (it shouldn't happen), returns the generic wallet.
    """
    exchange = Exchange.query.filter_by(id=id).first()
    if exchange:
        return exchange
    else:
        id = Params.GENERIC_WALLET
        exchange = Exchange.query.filter_by(id=id).first()
        return exchange


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


def get_exchange_choices(type=None):
    """Returns the list of exchanges available in 'Exchange' table,
    but in tuples so that it works with Input form choices.
    """
    if type:
        exchanges = Exchange.query.filter_by(type=type).all()
    else:
        exchanges = Exchange.query.all()
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


def get_withdraw_fee(exchange, coin):
    """Gets the withdraw fee of 'exchange'/'coin'.
    """
    withdraw_fee_1 = Fee.query.filter_by(exchange=exchange,
                                         action="Withdraw",
                                         scope=coin).first()
    if withdraw_fee_1:
        return withdraw_fee_1.amount
    return None


def get_exch_by_coin(coin):
    """Gets the exchanges that trade a given coin.
    """
    exchs = db.session.query(TradePair.exchange)\
                      .filter((TradePair.coin == coin) |
                              (TradePair.base_coin == coin))\
                      .distinct(TradePair.exchange).all()
    if exchs:
        return set([item[0] for item in exchs])
    return set()


def is_crypto(crypto):
    """Checks whether a coin is a crypto(True) or a fiat coin(False).
    """
    coin = Coin.query.filter_by(symbol=crypto).first()
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
