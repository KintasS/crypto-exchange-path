from secrets import token_hex
from crypto_exchange_path.config import Params
from crypto_exchange_path.utils_db import (calc_withdraw_fee, fx_exchange,
                                           is_crypto, get_exchange)
from crypto_exchange_path.utils import (num_2_str, round_amount,
                                        round_amount_by_price)


class Path:

    def __init__(self, path_type, origin,
                 hop_1, hop_2,
                 destination, currency, logger):
        self.id = 'a' + token_hex(4)
        self.type = path_type
        self.origin = origin
        self.hop_1 = hop_1
        self.hop_2 = hop_2
        self.destination = destination
        self.currency = currency
        self.logger = logger
        self.total_fees = self.calc_fees(currency, logger)

    def __repr__(self):
        return "Result(Type='{}', Origin='{}', Hop_1='{}', Hop_2='{}', "\
               "Destination='{}')".format(self.type,
                                          self.origin,
                                          self.hop_1,
                                          self.hop_2,
                                          self.destination)

    def get_total_fees(self, currency):
        return num_2_str(self.total_fees, currency)

    def fee_to_currency(self, amount, orig_coin):
        fee_curr = fx_exchange(orig_coin, self.currency, amount, self.logger)
        return num_2_str(fee_curr, self.currency)

    def calc_fees(self, currency, logger):
        """Calculates the overall path fees in the given 'currency'. Adds up:
        - Origin Withdraw fees (origin.withdraw_fee)
        - Hop 1 Trade fees (hop_1.trade.fee_amt)
        - Hop 1 Withdraw fees (hop_1.withdraw_fee)
        - Hop 2 Trade fees (hop_2.trade.fee_amt)
        - Hop 2 Withdraw fees (hop_2.withdraw_fee)
        """
        total_fees = 0
        # Add Origin Withdraw fees (origin.withdraw_fee)
        if self.origin.withdraw_fee:
            fee = fx_exchange(self.origin.coin.id,
                              currency,
                              self.origin.withdraw_fee,
                              logger)
            if fee:
                total_fees += fee
                msg = "calc_fees: {} = {} {} ({} {})"\
                    .format("origin.withdraw_fee",
                            self.origin.withdraw_fee,
                            self.origin.coin.id,
                            fee,
                            currency)
                logger.debug(msg)
        # Hop 1 Trade fees (hop_1.trade.fee_amt)
        if self.hop_1.trade.fee_amt:
            fee = fx_exchange(self.hop_1.trade.fee_coin.id,
                              currency,
                              self.hop_1.trade.fee_amt,
                              logger)
            if fee:
                total_fees += fee
                msg = "calc_fees: {} = {} {} ({} {})"\
                    .format("hop_1.trade.fee_amt",
                            self.hop_1.trade.fee_amt,
                            self.hop_1.trade.fee_coin.id,
                            fee,
                            currency)
                logger.debug(msg)
        # Add Hop 1 Withdraw fees (hop_1.withdraw_fee)
        if self.hop_1.withdraw_fee:
            fee = fx_exchange(self.hop_1.trade.buy_coin.id,
                              currency,
                              self.hop_1.withdraw_fee,
                              logger)
            if fee:
                total_fees += fee
                msg = "calc_fees: {} = {} {} ({} {})"\
                    .format("hop_1.withdraw_fee",
                            self.hop_1.withdraw_fee,
                            self.hop_1.trade.buy_coin.id,
                            fee,
                            currency)
                logger.debug(msg)
        # Add Hop 2 Trade fees (hop_2.trade.fee_amt)
        if self.hop_2 and self.hop_2.trade.fee_amt:
            fee = fx_exchange(self.hop_2.trade.fee_coin.id,
                              currency,
                              self.hop_2.trade.fee_amt,
                              logger)
            if fee:
                total_fees += fee
                msg = "calc_fees: {} = {} {} ({} {})"\
                    .format("hop_2.trade.fee_amt",
                            self.hop_2.trade.fee_amt,
                            self.hop_2.trade.fee_coin.id,
                            fee,
                            currency)
                logger.debug(msg)
        # Add Hop 2 Withdraw fees (hop_2.withdraw_fee)
        if self.hop_2 and self.hop_2.withdraw_fee:
            fee = fx_exchange(self.hop_2.trade.buy_coin.id,
                              currency,
                              self.hop_2.withdraw_fee,
                              logger)
            if fee:
                total_fees += fee
                msg = "calc_fees: {} = {} {} ({} {})"\
                    .format("hop_2.withdraw_fee",
                            self.hop_2.withdraw_fee,
                            self.hop_2.trade.buy_coin.id,
                            fee,
                            currency)
                logger.debug(msg)
        return total_fees


class Location:

    def __init__(self, type, exchange, amount, coin):
        self.type = type
        self.exchange = self.set_exchange(exchange, coin)
        self.amount = amount
        self.coin = coin
        self.withdraw_fee = None
        self.withdraw_details = None
        self.amount_str = self.calc_amt_str()
        self.store_withdraw_fee(exchange.id, coin.id, amount)

    def calc_amt_str(self):
        amount = round_amount_by_price(self.amount, self.coin.id)
        return "{} {}".format(amount, self.coin.id)

    def store_withdraw_fee(self, exchange, coin, amount):
        withdraw_fee = calc_withdraw_fee(exchange, coin, amount)
        self.withdraw_fee = withdraw_fee[0]
        self.withdraw_details = self.calc_withdraw_details(withdraw_fee)

    def calc_withdraw_details(self, withdraw_lit):
        lit = None
        if withdraw_lit:
            lit = withdraw_lit[1]
        literal = ("{} withdrawal fee for {}: {}")\
            .format(self.exchange.name,
                    self.coin.symbol,
                    lit)
        return literal

    def set_exchange(self, exchange, coin):
        """If the auxiliar exchange 'Wallet / Bank' was provided,
        it transforms it to the appropriate one.
        """
        if exchange.id != Params.AUX_EXCHANGE:
            return exchange
        else:
            if is_crypto(coin.id):
                return get_exchange('Wallet')
            else:
                return get_exchange('Bank')

    def __repr__(self):
        return "Location({}: {} [{} {}]').".format(self.type,
                                                   self.exchange.id,
                                                   self.amount,
                                                   self.coin)


class Hop:

    def __init__(self, exchange, trade, withdraw_fee):
        self.exchange = exchange
        self.trade = trade
        self.withdraw_fee = self.store_withdraw_fee(withdraw_fee)
        self.trade_details = self.calc_trade_details()
        self.withdraw_details = self.calc_withdraw_details(withdraw_fee)

    def store_withdraw_fee(self, withdraw_fee):
        if withdraw_fee and withdraw_fee[0] is not None:
            return withdraw_fee[0]
        else:
            return None

    def calc_trade_details(self):
        rate = round_amount(self.trade.buy_amt / self.trade.sell_amt)
        literal = ("{}/{} rate: {}. {} trading fee: {}")\
            .format(self.trade.buy_coin.symbol,
                    self.trade.sell_coin.symbol,
                    rate,
                    self.exchange.name,
                    self.trade.fee_literal)
        return literal

    def calc_withdraw_details(self, withdraw_lit):
        lit = None
        if withdraw_lit:
            lit = withdraw_lit[1]
        literal = ("{} withdrawal fee for {}: {}")\
            .format(self.exchange.name,
                    self.trade.buy_coin.symbol,
                    lit)
        return literal

    def __repr__(self):
        return "Hop([{}] {}. Withdraw fee='{}')."\
            .format(self.exchange.id,
                    self.trade,
                    self.withdraw_fee)


class Trade:

    def __init__(self, sell_amt, sell_coin,
                 buy_amt, buy_coin,
                 fee_amt, fee_coin, fee_literal):
        self.sell_amt = sell_amt
        self.sell_coin = sell_coin
        self.buy_amt = buy_amt
        self.buy_coin = buy_coin
        self.fee_amt = fee_amt
        self.fee_coin = fee_coin
        self.fee_literal = fee_literal
        self.sell_amt_str = self.calc_amt_str(self.sell_amt,
                                              self.sell_coin.id)
        self.buy_amt_str = self.calc_amt_str(self.buy_amt,
                                             self.buy_coin.id)
        self.fee_amt_str = self.calc_amt_str(self.fee_amt,
                                             self.fee_coin.id)

    def calc_amt_str(self, amt, coin):
        amount = round_amount_by_price(amt, coin)
        return "{} {}".format(amount, coin)

    def __repr__(self):
        return "Trade(Sell='{} {}', Buy='{} {}', Fee='{} {}')"\
            .format(self.sell_amt, self.sell_coin.id,
                    self.buy_amt, self.buy_coin.id,
                    self.fee_amt, self.fee_coin.id)


class CoinZ:
    """Within the scope of an exchange, it represents an Object that trades
    both against 'coin' and 'base_coin' and has the highest liquidity against
    them.
    The object contains the coin object and the liquidity against
    the two coins.
    """

    def __init__(self, coin, liq_vs_coin,
                 liq_vs_base_coin):
        self.coin = coin
        self.liq_vs_coin = liq_vs_coin
        self.liq_vs_base_coin = liq_vs_base_coin

    def __repr__(self):
        return "CoinZ({} [Liq.Coin={}, Liq.BaseCoin={}])"\
            .format(self.coin.id, self.liq_vs_coin, self.liq_vs_base_coin)

    def min_liq(self):
        """Returns the smaller liquidity of CoinZ ('liq_vs_coin' or
        'liq_vs_base_coin')
        """
        return min(self.liq_vs_coin, self.liq_vs_base_coin)
