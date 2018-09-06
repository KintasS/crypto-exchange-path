from crypto_exchange_path.models import Fee, TradePair
from crypto_exchange_path.objects import Trade, CoinZ
from crypto_exchange_path import db
from crypto_exchange_path.utils_db import is_crypto, fx_exchange, get_coin


class ExchangeManager(object):

    def __init__(self, exchange, fee_settings, logger):
        self.exchange = exchange
        self.logger = logger
        self.fee_settings = fee_settings
        self.default_fee = self.get_fee_setting("Default")
        self.special_fee = self.get_fee_setting(exchange.id)
        self.cep_promo = self.get_fee_setting("CEP")
        self.coinZs = None

    def get_fee_setting(self, key):
        """Gets a fee setting from the 'fee_settings' dictionary.
        """
        try:
            return self.fee_settings[key]
        except KeyError as e:
            return None

    def calc_fee_literal(self, fee, scope):
        """Auxiliar function for 'get_trade_fee'.
        Calcs the fee literal to be later shown in the website.
        """
        if scope == "(Maker)":
            scope_str = "(for Market Makers)"
        elif scope == "(Taker)":
            scope_str = "(for Market Takers)"
        elif scope == "(BNB)":
            scope_str = "(when paid in BNB)"
        else:
            scope_str = "({} trades)".format(scope)
        return "{}% {}".format(fee, scope_str)

    def get_trade_fee(self, sell_amt, sell_coin, buy_coin):
        """Get the trade fee to be applied.
        Returns a tuple: [<amount%>, <coin_object>, <fee_literal>].
        """
        # Get trading fees for the exchange
        exch_trade_fees = Fee.query.filter_by(exchange=self.exchange.id,
                                              action='Trade').all()
        # Check whether the query found fees
        if not exch_trade_fees:
            self.logger.warning("perform_trade: No trade fees "
                                "found for exchange'{}'. Skipping trade "
                                "calculation for '{}/{}'"
                                .format(self.exchange.id,
                                        sell_coin.id,
                                        buy_coin.id))
            return None
        # Generate trade_pair to look for it in fees
        trade_pair = "{}/{}".format(sell_coin.id,
                                    buy_coin.id)
        # Find the trading fee for the given pair
        return_fee = [None, None]
        cep_promo_found = False
        special_fee_found = False
        pair_fee_found = False
        for fee in exch_trade_fees:
            # First look for our promos
            if fee.scope == self.cep_promo:
                cep_promo_found = True
                fee_literal = self.calc_fee_literal(fee.amount, fee.scope)
                return_fee = [fee.amount, fee.fee_coin, fee_literal]
            # Then look for special fees of the exchange
            elif fee.scope == self.special_fee:
                if not cep_promo_found:
                    special_fee_found = True
                    fee_literal = self.calc_fee_literal(fee.amount, fee.scope)
                    return_fee = [fee.amount, fee.fee_coin, fee_literal]
            # Then look for special fees for given pairs
            elif fee.scope in trade_pair:
                if not cep_promo_found and not special_fee_found:
                    pair_fee_found = True
                    fee_literal = self.calc_fee_literal(fee.amount, fee.scope)
                    return_fee = [fee.amount, fee.fee_coin, fee_literal]
            # Finally, look for the default fee
            elif fee.scope == self.default_fee:
                if (not cep_promo_found and not special_fee_found
                        and not pair_fee_found):
                    fee_literal = self.calc_fee_literal(fee.amount, fee.scope)
                    return_fee = [fee.amount, fee.fee_coin, fee_literal]
        return return_fee

    def perform_trade(self, sell_amt, sell_coin, buy_coin):
        """Performs the trade from 'sell_coin' to 'buy_coin'.
        Returns a 'Trade' object
        """
        # Find the trading fee for the given pair
        fee_amt_perc, fee_coin, fee_literal = self.get_trade_fee(sell_amt,
                                                                 sell_coin,
                                                                 buy_coin)
        if fee_amt_perc is None:
            self.logger.warning("perform_trade: No trade fee for '{}[{}/{}]'."
                                "Skipping trade calculation."
                                .format(self.exchange.id,
                                        sell_coin.id,
                                        buy_coin.id))
            return None
        # Perform trade:
        buy_amt = fx_exchange(sell_coin.id,
                              buy_coin.id,
                              sell_amt * (1 - fee_amt_perc / 100),
                              self.logger)
        if buy_amt is None:
            self.logger.warning("perform_trade [2]: Trade could not be "
                                "performed '{}[{}/{}]'. "
                                "Skipping trade calculation."
                                .format(self.exchange.id,
                                        sell_coin.id,
                                        buy_coin.id))
            return None
        # Fees calculated by default in 'sell_coin'
        fee_amt = fee_amt_perc / 100 * sell_amt
        # If 'FeeCoin' has a value, calculate fees in 'FeeCoin'
        if fee_coin and fee_coin is not '-':
            fee_amt = fx_exchange(sell_coin.id,
                                  fee_coin,
                                  fee_amt,
                                  self.logger)
            fee_coin = get_coin(fee_coin)
        else:
            fee_coin = sell_coin
        # Return calculated trade
        self.logger.debug("perform_trade [3]: Trade for '{}[{}/{}]:"
                          " Sell={} {} / Buy={} {} / Fee={} {}'"
                          "".format(self.exchange.id, sell_coin.id,
                                    buy_coin.id, sell_amt, sell_coin.id,
                                    buy_amt, buy_coin.id,
                                    fee_amt, fee_coin.id))
        return Trade(sell_amt, sell_coin,
                     buy_amt, buy_coin,
                     fee_amt, fee_coin, fee_literal)

    def get_all_coinZs(self, coin):
        """Gets all the coins (cryptos & fiat) that trade in the exchange
        against the given coin.
        The liquidity needs to be higher than the given liquidity.
        Returns a list: [[<coinZ_1>,<liq_1>],[<coinZ_2>,<liq_2>],...)
        """
        # Get CoinZ's that trade against 'coin' (Coin='coin')
        coinZs = db.session.query(TradePair)\
                           .filter((TradePair.exchange == self.exchange.id) &
                                   (TradePair.coin == coin)).all()
        coinZs = [(item.base_coin, item.volume) for item in coinZs]
        # Get CoinZ's that trade against 'coin' (BaseCoin='coin')
        coinZs_aux = db.session.query(TradePair)\
                               .filter((TradePair.exchange == self.exchange.id)
                                       & (TradePair.base_coin == coin)).all()
        coinZs_aux = [(item.coin, item.volume) for item in coinZs_aux]
        if coinZs_aux:
            coinZs += coinZs_aux
        # Return results
        self.logger.debug("get_all_coinZs: [{}] CoinZ's against '{}' [{}]: {}"
                          .format(self.exchange.id, coin, len(coinZs), coinZs))
        return set(coinZs)

    def get_all_cryptoZs(self, coin):
        """Gets all the cryptos (not Fiat) that trade in the exchange
        against the given coin. Manually removes 'USDT' as well.
        Returns a list: [[<coinZ_1>,<liq_1>],[<coinZ_2>,<liq_2>],...)
        """
        # Get all coinZs (crypto & Fiat)
        cryptoZs = self.get_all_coinZs(coin)
        # Remove fiat coins & USDT
        result_cryptoZs = []
        for item in cryptoZs:
            if is_crypto(item[0]) and (item[0] != 'USDT'):
                result_cryptoZs.append(item)
        return result_cryptoZs

    def get_best_coinZ(self, coin, baseCoin):
        """Finds a coin that trades in the exchange against both given coins.
        Returns a 'CoinZ' object.
        """
        # Get CoinZ's that trade against 'coin' & 'baseCoin'
        coinZ_coin = self.get_all_coinZs(coin)
        coinZ_baseCoin = self.get_all_coinZs(baseCoin)
        # Find CoinZ that trades agains both coins with highest liquidity
        winning_coinZ = CoinZ(None, -1, -1)
        for coinZ in coinZ_coin:
            for coinZ_2 in coinZ_baseCoin:
                if coinZ[0] == coinZ_2[0]:
                    if min(coinZ[1], coinZ_2[1]) < winning_coinZ.min_liq():
                        continue
                    # If same liquidity (or no available), BTC prevails
                    elif min(coinZ[1], coinZ_2[1]) == winning_coinZ.min_liq():
                        if (winning_coinZ.coin
                                and winning_coinZ.coin.id == 'BTC'):
                            continue
                    winning_coinZ = CoinZ(get_coin(coinZ[0]),
                                          coinZ[1],
                                          coinZ_2[1])
        if not winning_coinZ.coin:
            return None
        self.logger.debug("[{}] Chosen CoinZ: {}"
                          .format(self.exchange.id, winning_coinZ))
        return winning_coinZ
