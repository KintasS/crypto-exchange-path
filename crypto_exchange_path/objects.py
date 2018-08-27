from secrets import token_hex
from crypto_exchange_path.utils_db import (get_withdraw_fee, fx_exchange,
                                           round_amount)
from crypto_exchange_path.utils import num_2_str


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
        # self.steps = self.calc_steps(logger)

    def __repr__(self):
        return "Result(Type='{}', Origin='{}', Hop_1='{}', Hop_2='{}', "\
               "Destination='{}')".format(self.type,
                                          self.origin,
                                          self.hop_1,
                                          self.hop_2,
                                          self.destination)

    def get_total_fees(self, currency, decs=None):
        return num_2_str(self.total_fees, currency, decs)

    def fee_to_currency(self, amount, orig_coin):
        fee_curr = fx_exchange(orig_coin, self.currency, amount, self.logger)
        return num_2_str(fee_curr, self.currency, None)

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
        self.exchange = exchange
        self.amount = amount
        self.coin = coin
        self.withdraw_fee = get_withdraw_fee(self.exchange.id,
                                             self.coin.id)
        self.amount_str = self.calc_amt_str()

    def calc_amt_str(self):
        amount = round_amount(self.amount, self.coin.id)
        return "{} {}".format(amount, self.coin.id)

    def __repr__(self):
        return "Location({}: {} [{} {}]').".format(self.type,
                                                   self.exchange.id,
                                                   self.amount,
                                                   self.coin)


class Hop:

    def __init__(self, exchange, trade, volume, withdraw_fee):
        self.exchange = exchange
        self.trade = trade
        self.volume = volume
        self.withdraw_fee = withdraw_fee

    def __repr__(self):
        return "Hop([{}] {}. Vol={}. Withdraw fee='{}')."\
            .format(self.exchange.id,
                    self.trade,
                    self.volume,
                    self.withdraw_fee)


class Trade:

    def __init__(self, sell_amt, sell_coin,
                 buy_amt, buy_coin,
                 fee_amt, fee_coin):
        self.sell_amt = sell_amt
        self.sell_coin = sell_coin
        self.buy_amt = buy_amt
        self.buy_coin = buy_coin
        self.fee_amt = fee_amt
        self.fee_coin = fee_coin
        self.sell_amt_str = self.calc_amt_str(self.sell_amt,
                                              self.sell_coin.id)
        self.buy_amt_str = self.calc_amt_str(self.buy_amt,
                                             self.buy_coin.id)
        self.fee_amt_str = self.calc_amt_str(self.fee_amt,
                                             self.fee_coin.id)

    def calc_amt_str(self, amt, coin):
        amount = round_amount(amt, coin)
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
