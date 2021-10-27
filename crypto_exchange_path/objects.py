from secrets import token_hex
from flask import Markup
from crypto_exchange_path.config import Params
from crypto_exchange_path.utils_db import calc_fee, fx_exchange
from crypto_exchange_path.utils import (num_2_str, round_amount, str_2_float,
                                        round_amount_by_price,
                                        round_amount_by_price_str, is_number)


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

    def calc_transfer_fees(self, fee_lst, coin, to_curr=False):
        """ Returns a string that contains the sum of the fees provided in
        'fee_lst' (withdrawal & deposit fees).
        If 'to_curr' is equal to 'True', the function converts the sum
        to the calculation currency.
        """
        fee_sum = sum(filter(None, fee_lst))
        # Remove decimals if round number
        if fee_sum - round(fee_sum) == 0:
            fee_sum = round(fee_sum)
        if fee_sum is not None:
            if to_curr:
                fee_sum = fx_exchange(coin.id,
                                      self.currency,
                                      fee_sum,
                                      self.logger)
                return num_2_str(fee_sum, self.currency)
            else:
                return "{} {}".format(fee_sum, coin.symbol)
        else:
            return ""

    def calc_fees(self, currency, logger):
        """Calculates the overall path fees in the given 'currency'. Adds up:
        - Origin Withdraw fees (origin.withdraw_fee)
        - Hop 1 Deposit fees (hop_1.deposit_fee)
        - Hop 1 Trade fees (hop_1.trade.fee_amt)
        - Hop 1 Withdraw fees (hop_1.withdraw_fee)
        - Hop 2 Deposit fees (hop_2.deposit_fee)
        - Hop 2 Trade fees (hop_2.trade.fee_amt)
        - Hop 2 Withdraw fees (hop_2.withdraw_fee)
        - Destination Deposit fees (destination.deposit_fee)
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
        # Hop 1 Deposit fees (hop_1.deposit_fee)
        if self.hop_1.deposit_fee:
            fee = fx_exchange(self.hop_1.trade.sell_coin.id,
                              currency,
                              self.hop_1.deposit_fee,
                              logger)
            if fee:
                total_fees += fee
                msg = "calc_fees: {} = {} {} ({} {})"\
                    .format("hop_1.deposit_fee",
                            self.hop_1.deposit_fee,
                            self.hop_1.trade.sell_coin.id,
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
        # Add Hop 2 Deposit fees (hop_2.deposit_fee)
        if self.hop_2 and self.hop_2.deposit_fee:
            fee = fx_exchange(self.hop_2.trade.sell_coin.id,
                              currency,
                              self.hop_2.deposit_fee,
                              logger)
            if fee:
                total_fees += fee
                msg = "calc_fees: {} = {} {} ({} {})"\
                    .format("hop_2.deposit_fee",
                            self.hop_2.deposit_fee,
                            self.hop_2.trade.sell_coin.id,
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
        # Add Destination Deposit fees (destination.deposit_fee)
        if self.destination.deposit_fee:
            fee = fx_exchange(self.destination.coin.id,
                              currency,
                              self.destination.deposit_fee,
                              logger)
            if fee:
                total_fees += fee
                msg = "calc_fees: {} = {} {} ({} {})"\
                    .format("destination.deposit_fee",
                            self.destination.deposit_fee,
                            self.destination.coin.id,
                            fee,
                            currency)
                logger.debug(msg)
        return total_fees


class Location:

    def __init__(self, type, exchange, amount, coin, logger):
        self.type = type
        self.exchange = exchange
        self.amount = amount
        self.coin = coin
        self.deposit_fee = None
        self.deposit_details = None
        self.withdraw_fee = None
        self.withdraw_details = None
        self.amount_str = self.calc_amt_str()
        self.logger = logger
        self.store_fee('Deposit', exchange.id, coin, amount)
        self.store_fee('Withdrawal', exchange.id, coin, amount)

    def calc_amt_str(self):
        amount = round_amount_by_price_str(self.amount, self.coin)
        return "{} {}".format(amount, self.coin.symbol)

    def store_fee(self, action, exchange, coin, amount):
        """ Stores the deposit or withdrawal fee.
        """
        fee_array = calc_fee(action, exchange, coin, amount, self.logger)
        if action == 'Deposit':
            self.deposit_fee = fee_array[0]
            self.deposit_details = self.calc_fee_details(action, fee_array)
            # If there are deposit fees for 'Destination', substract from amt
            if self.type == 'Destination' and self.deposit_fee:
                self.amount -= self.deposit_fee
                self.amount_str = self.calc_amt_str()
        if action == 'Withdrawal':
            self.withdraw_fee = fee_array[0]
            self.withdraw_details = self.calc_fee_details(action, fee_array)

    def remove_deposit_fees(self):
        self.deposit_fee = None
        self.deposit_details = None

    def calc_fee_details(self, action, fee_lit):
        if fee_lit and fee_lit[1] is not None:
            fee_type = 'withdrawal'
            if action == 'Deposit':
                fee_type = 'deposit'
            lit = fee_lit[1]
            literal = ("{} {} fee for {}: {}.")\
                .format(self.exchange.name,
                        fee_type,
                        self.coin.symbol,
                        lit)
            return literal
        return ""

    def __repr__(self):
        return "Location({}: {} [{} {}]').".format(self.type,
                                                   self.exchange.id,
                                                   self.amount,
                                                   self.coin)


class Hop:

    def __init__(self, exchange, trade, deposit_fee, withdraw_fee):
        self.exchange = exchange
        self.exch_promo = self.get_exch_promo(exchange)
        self.trade = trade
        self.deposit_fee = None
        self.withdraw_fee = None
        self.trade_details = self.calc_trade_details()
        self.deposit_details = self.calc_fee_details('Deposit', deposit_fee)
        self.withdraw_details = self.calc_fee_details('Withdrawal',
                                                      withdraw_fee)
        self.store_fees(deposit_fee, withdraw_fee)

    def get_exch_promo(self, exchange):
        """Checks whether the exchange has a user promo, in which case adds
        the promo text. Otherwise it returns None.
        """
        if exchange.id in Params.USER_PROMOS_FOR_RESULTS:
            return Markup(Params.USER_PROMOS_FOR_RESULTS[exchange.id])
        else:
            return None

    def store_fees(self, deposit_fee, withdraw_fee):
        if deposit_fee and deposit_fee[0] is not None:
            rounded_fee = round_amount_by_price(deposit_fee[0],
                                                self.trade.sell_coin.symbol)
            # Ensure that it is stored as a float
            if is_number(rounded_fee):
                self.deposit_fee = rounded_fee
            else:
                self.deposit_fee = str_2_float(rounded_fee)
        if withdraw_fee and withdraw_fee[0] is not None:
            rounded_fee = round_amount_by_price(withdraw_fee[0],
                                                self.trade.buy_coin.symbol)
            # Ensure that it is stored as a float
            if is_number(rounded_fee):
                self.withdraw_fee = rounded_fee
            else:
                self.withdraw_fee = str_2_float(rounded_fee)

    def calc_trade_details(self):
        rate = round_amount(self.trade.sell_amt / self.trade.buy_amt)
        literal = ("{}/{} rate: {}.<br>- - -</br> {} trading fee: {}")\
            .format(self.trade.buy_coin.symbol,
                    self.trade.sell_coin.symbol,
                    rate,
                    self.exchange.name,
                    self.trade.fee_literal)
        return literal

    def calc_fee_details(self, action, fee_array):
        if fee_array and fee_array[1] is not None:
            fee_type = 'withdrawal'
            coin = self.trade.buy_coin.symbol
            if action == 'Deposit':
                fee_type = 'deposit'
                coin = self.trade.sell_coin.symbol
            literal = ("{} {} fee for {}: {}.")\
                .format(self.exchange.name,
                        fee_type,
                        coin,
                        fee_array[1])
            return literal
        return ""

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
                                              self.sell_coin)
        self.buy_amt_str = self.calc_amt_str(self.buy_amt,
                                             self.buy_coin)
        self.fee_amt_str = self.calc_amt_str(self.fee_amt,
                                             self.fee_coin)

    def calc_amt_str(self, amt, coin):
        amount = round_amount_by_price_str(amt, coin)
        return "{} {}".format(amount, coin.symbol)

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
