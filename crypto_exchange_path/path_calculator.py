from crypto_exchange_path.utils_db import (get_exch_by_pair, get_exch_by_coin,
                                           get_coin, get_exchange,
                                           calc_withdraw_fee)
from crypto_exchange_path.utils import generate_paths_file
from crypto_exchange_path.exchange_manager import ExchangeManager
from crypto_exchange_path.objects import Location, Hop, Path


def calc_paths(orig_loc, orig_coin, orig_amt, dest_loc, dest_coin,
               connection_type, user_exchanges, currency, fee_settings,
               logger):

    # Paths container
    path_list = []

    """ ***********************************************************************
    ***************************************************************************
    1. DIRECT EXCHANGE(NO HOPS)
    ***************************************************************************
    *********************************************************************** """

    logger.info("STARTING CALCULATION FOR: \norig_amt = {} \norig_coin = {}"
                "\norig_loc = {} \ndest_coin = {} \ndest_loc = {} "
                "\nconnection_type = {} \nuser_exchanges = {}"
                "\ncurrency = {} \nfee_settings = {}"
                .format(orig_amt, orig_coin, orig_loc, dest_coin, dest_loc,
                        connection_type, user_exchanges, currency,
                        fee_settings))

    logger.info("Main: CALCULATING '1. DIRECT EXCHANGE(NO HOPS)'")
    # Get exchanges with direct pair exchange
    direct_pair_exch = get_exch_by_pair(orig_coin.id,
                                        dest_coin.id,
                                        logger)
    # Filter exchanges with user preferences
    if user_exchanges:
        filtered_exch = set()
        for exch in direct_pair_exch:
            if exch in user_exchanges:
                filtered_exch.add(exch)
        direct_pair_exch = filtered_exch
        logger.debug("Exchanges filtered by user pref.: {}"
                     .format(direct_pair_exch))
    # Common parts of 'Path'
    path_type = '[1] Direct (1 Exch)'
    origin = Location("Origin", orig_loc, orig_amt, orig_coin)

    # Loop for each exchange to calculate Path fees
    for exch in direct_pair_exch:
        trade_1_sell_amt = orig_amt
        if origin.withdraw_fee:
            trade_1_sell_amt -= origin.withdraw_fee
        exchange_1 = ExchangeManager(get_exchange(exch), fee_settings, logger)
        trade_1 = exchange_1.perform_trade(trade_1_sell_amt,
                                           orig_coin,
                                           dest_coin)
        # If 'perform_trade()' did not get results, skip path. Else continue
        if not trade_1:
            logger.warning("Main: Trade could not be performed for {}/{}[{}]. "
                           "Path skipped.".format(orig_coin.id,
                                                  dest_coin.id,
                                                  exch))
            continue
        # Calc destination amount
        dest_amt = trade_1.buy_amt
        # Calc Withdraw fee and modify destination amount
        withdraw_fee_1 = None
        if exch != dest_loc.id:
            withdraw_fee_1 = calc_withdraw_fee(exch, trade_1.buy_coin.id,
                                               trade_1.buy_amt)
            if withdraw_fee_1 is not None:
                dest_amt -= withdraw_fee_1
            else:
                logger.warning("Main: Withdraw Fee not found for {} [{}]. "
                               "Path skipped.".format(exch,
                                                      trade_1.buy_coin.id))
                continue
        # Generate Hop & destination location to finish 'Path'
        hop_1 = Hop(get_exchange(exch),
                    trade_1,
                    -1,  # BORRAR VOLUMEN
                    withdraw_fee_1)
        destination = Location("Destination", dest_loc, dest_amt, dest_coin)
        # Generate 'Path' and add to 'path_list'
        path = Path(path_type, origin, hop_1, None,
                    destination, currency, logger)
        path_list.append(path)
        logger.debug(('Path Found: {}->{}({})').format(trade_1.sell_coin.id,
                                                       trade_1.buy_coin.id,
                                                       exch))
    logger.info("End of '1. DIRECT EXCHANGE(NO HOPS)'")
    # If user selected 'Direct Exchanges', generate results and return
    if (connection_type == '0'):
        # generate_paths_file(path_list, currency, logger)
        logger.info("Path calculation finished. '{}' results"
                    .format(len(path_list)))
        return path_list

    """ ***********************************************************************
    ***************************************************************************
    2. INDIRECT EXCHANGE(ONE HOP)
    ***************************************************************************
    *********************************************************************** """
    logger.info("Main: CALCULATING '2. INDIRECT EXCHANGE(ONE HOP)'")
    # Get exchanges with indirect pair exchange
    orig_coin_exchanges = get_exch_by_coin(orig_coin.id)
    dest_coin_exchanges = get_exch_by_coin(dest_coin.id)
    # Filter exchanges with user preferences and already used
    if user_exchanges:
        # Filter 'orig_coin_exchanges'
        filtered_exch = set()
        for exch in orig_coin_exchanges:
            if (exch in user_exchanges) and (exch not in direct_pair_exch):
                filtered_exch.add(exch)
        orig_coin_exchanges = filtered_exch
        logger.debug("Main: 'orig_coin_exchanges' filtered: {}"
                     .format(orig_coin_exchanges))
        # Filter 'dest_coin_exchanges'
        filtered_exch = set()
        for exch in dest_coin_exchanges:
            if (exch in user_exchanges) and (exch not in direct_pair_exch):
                filtered_exch.add(exch)
        dest_coin_exchanges = filtered_exch
        logger.debug("Main: 'dest_coin_exchanges' filtered: {}"
                     .format(dest_coin_exchanges))
    # Filter exchanges already used
    else:
        # Filter 'orig_coin_exchanges'
        filtered_exch = set()
        for exch in orig_coin_exchanges:
            if exch not in direct_pair_exch:
                filtered_exch.add(exch)
        orig_coin_exchanges = filtered_exch
        logger.debug("Main: 'orig_coin_exchanges' filtered: {}"
                     .format(orig_coin_exchanges))
        # Filter 'dest_coin_exchanges'
        filtered_exch = set()
        for exch in dest_coin_exchanges:
            if exch not in direct_pair_exch:
                filtered_exch.add(exch)
        dest_coin_exchanges = filtered_exch
        logger.debug("Main: 'dest_coin_exchanges' filtered: {}"
                     .format(dest_coin_exchanges))
    # Select exchanges that trade both coins, but not with a direct trade
    indirect_pair_exch = [exch for exch in orig_coin_exchanges
                          if exch in dest_coin_exchanges]
    logger.debug("Exchanges with both pairs (but not direct trade) [{}]: {}"
                 "".format(len(indirect_pair_exch), indirect_pair_exch))
    # Common parts of 'Path'
    path_type = '[2] Indirect (1 Exch)'
    origin = Location("Origin", orig_loc, orig_amt, orig_coin)
    # Loop for each exchange with both pairs
    for exch in indirect_pair_exch:
        # Get CoinZ that trades against both pairs
        exchange = ExchangeManager(get_exchange(exch), fee_settings, logger)
        coinZ = exchange.get_best_coinZ(orig_coin.id,
                                        dest_coin.id)
        if not coinZ:
            logger.warning("Main: No coinZ found in exchange '{}' to convert"
                           "'{}' to '{}' Path skipped.".format(exch,
                                                               orig_coin.id,
                                                               dest_coin.id))
            continue
        # CALCULATE OUTPUTS FOR 'Hop 1'
        trade_1_sell_amt = orig_amt
        if origin.withdraw_fee:
            trade_1_sell_amt -= origin.withdraw_fee
        trade_1 = exchange.perform_trade(trade_1_sell_amt,
                                         orig_coin,
                                         coinZ.coin)
        # If 'perform_trade()' did not get results, skip path. Else continue
        if not trade_1:
            logger.warning("Main: Trade could not be performed for {}/{}[{}]. "
                           "Path skipped.".format(orig_coin.id,
                                                  coinZ.coin.id,
                                                  exch))
            continue
        # Generate output object for 'Hop 1'
        hop_1 = Hop(exchange.exchange,
                    trade_1,
                    coinZ.liq_vs_coin,
                    None)
        # CALCULATE OUTPUTS FOR 'Hop 2'
        trade_2 = exchange.perform_trade(trade_1.buy_amt,
                                         trade_1.buy_coin,
                                         dest_coin)
        # If 'perform_trade()' did not get results, skip path. Else continue
        if not trade_2:
            logger.warning("Main: Trade could not be performed for {}/{}[{}]. "
                           "Path skipped.".format(trade_1.buy_coin.id,
                                                  dest_coin.id,
                                                  exch))
            continue
        # Calc destination amount
        dest_amt = trade_2.buy_amt
        # Calc Withdraw fee and modify destination amount
        withdraw_fee_2 = None
        if exch != dest_loc.id:
            withdraw_fee_2 = calc_withdraw_fee(exch, trade_2.buy_coin.id,
                                               trade_2.buy_amt)
            if withdraw_fee_2 is not None:
                dest_amt -= withdraw_fee_2
            else:
                logger.warning("Main: Withdraw Fee not found for {} [{}]. "
                               "Path skipped.".format(exch,
                                                      trade_2.buy_coin.id))
                continue
        # Generate Hop & destination location to finish 'Path'
        hop_2 = Hop(exchange.exchange,
                    trade_2,
                    coinZ.liq_vs_base_coin,
                    withdraw_fee_2)
        destination = Location("Destination", dest_loc, dest_amt, dest_coin)
        # Generate 'Path' and add to 'path_list'
        path = Path(path_type, origin,
                    hop_1, hop_2,
                    destination, currency, logger)
        path_list.append(path)
        logger.debug('Path Found: {}->{}({})'
                     ' --> {}->{}({})'.format(trade_1.sell_coin.id,
                                              trade_1.buy_coin.id,
                                              exch,
                                              trade_2.sell_coin.id,
                                              trade_2.buy_coin.id,
                                              exch))
    logger.info("End of '2. INDIRECT EXCHANGE(ONE HOP)'")
    # If user selected 'One connection', generate results and return
    if (connection_type == '1'):
        # generate_paths_file(path_list, currency, logger)
        logger.info("Path calculation finished. '{}' results"
                    .format(len(path_list)))
        return path_list

    """ ***********************************************************************
    ***************************************************************************
    3. INDIRECT EXCHANGE(TWO HOPS)
    ***************************************************************************
    *********************************************************************** """
    logger.info("Main: CALCULATING '3. INDIRECT EXCHANGE(TWO HOPS)'")
    # Get all the coins that trade against 'orig_coin' for each exchange
    orig_coin_exchanges_coinZs = []
    for exch in orig_coin_exchanges:
        exchange = ExchangeManager(get_exchange(exch), fee_settings, logger)
        coinZs_A = exchange.get_all_cryptoZs(orig_coin.id)
        exchange.coinZs = coinZs_A
        orig_coin_exchanges_coinZs.append(exchange)
        logger.debug("Pairs against [] {}: {}".format(exchange.exchange.id,
                                                      orig_coin.id,
                                                      exchange.coinZs))
    # Get all the coins that trade against 'dest_coin' for each exchange
    dest_coin_exchanges_coinZs = []
    for exch in dest_coin_exchanges:
        exchange = ExchangeManager(get_exchange(exch), fee_settings, logger)
        coinZs_B = exchange.get_all_cryptoZs(dest_coin.id)
        exchange.coinZs = coinZs_B
        dest_coin_exchanges_coinZs.append(exchange)
        logger.debug("Pairs against [] {}: {}".format(exchange.exchange.id,
                                                      orig_coin.id,
                                                      exchange.coinZs))
    # Common parts of 'Path'
    path_type = '[3] Indirect (2 Exchanges)'
    origin = Location("Origin", orig_loc, orig_amt, orig_coin)
    # Loop through all the exchanges and coins
    for exch_A in orig_coin_exchanges_coinZs:
        for coinZ_A in exch_A.coinZs:
            for exch_B in dest_coin_exchanges_coinZs:
                if exch_A.exchange.id == exch_B.exchange.id:
                    continue
                for coinZ_B in exch_B.coinZs:
                    # If coinZ_A==coinZ_B, calculate Exchange Path
                    if coinZ_A[0] == coinZ_B[0]:
                        # CALCULATE OUTPUTS FOR 'Hop 1'
                        trade_1_sell_amt = orig_amt
                        if origin.withdraw_fee:
                            trade_1_sell_amt -= origin.withdraw_fee
                        trade_1 = exch_A.perform_trade(trade_1_sell_amt,
                                                       orig_coin,
                                                       get_coin(coinZ_A[0]))
                        # If 'perform_trade()' did not get results, skip path
                        if not trade_1:
                            logger.warning("Main: Trade could not be performed"
                                           " for {}/{}[{}]. Path skipped."
                                           .format(orig_coin.id,
                                                   coinZ_A[0],
                                                   exch_A.exchange.id))
                            continue
                        # Calc destination amount
                        in_amt_2 = trade_1.buy_amt
                        # Calc Withdraw fee and modify destination amount
                        withdraw_fee_1 = calc_withdraw_fee(exch_A.exchange.id,
                                                           trade_1.buy_coin.id,
                                                           trade_1.buy_amt)
                        if withdraw_fee_1 is not None:
                            in_amt_2 -= withdraw_fee_1
                        else:
                            logger.warning("Main: Withdraw Fee not found for"
                                           " {} [{}]. Path skipped."
                                           .format(exch_A.exchange.id,
                                                   trade_1.buy_coin.id))
                            continue
                        # Generate output object for 'Hop 1'
                        hop_1 = Hop(exch_A.exchange,
                                    trade_1,
                                    coinZ_A[1],
                                    withdraw_fee_1)
                        # CALCULATE OUTPUTS FOR 'Hop 2'
                        trade_2 = exch_B.perform_trade(in_amt_2,
                                                       trade_1.buy_coin,
                                                       dest_coin)
                        # If 'perform_trade()' did not get results, skip path
                        if not trade_2:
                            logger.warning("Main: Trade could not be performed"
                                           " for {}/{}[{}]. Path skipped."
                                           .format(trade_1.buy_coin.id,
                                                   dest_coin.id,
                                                   exch_B.exchange.id))
                            continue
                        # Calc destination amount
                        dest_amt = trade_2.buy_amt
                        # Calc Withdraw fee and modify destination amount
                        withdraw_fee_2 = None
                        if exch_B.exchange.id != dest_loc.id:
                            withdraw_fee_2 = calc_withdraw_fee(exch_B.exchange
                                                               .id,
                                                               trade_2
                                                               .buy_coin.id,
                                                               trade_2.buy_amt)
                            if withdraw_fee_2 is not None:
                                dest_amt -= withdraw_fee_2
                            else:
                                logger.warning("Main: Withdraw Fee not found "
                                               "for {} [{}]. Path skipped."
                                               .format(exch_B.exchange.id,
                                                       trade_2.buy_coin.id))
                                continue
                        # Generate Hop & destination location to finish 'Path'
                        hop_2 = Hop(exch_B.exchange,
                                    trade_2,
                                    coinZ_A[1],
                                    withdraw_fee_2)
                        destination = Location("Destination",
                                               dest_loc,
                                               dest_amt,
                                               dest_coin)
                        # Generate 'Path' and add to 'path_list'
                        path = Path(path_type, origin,
                                    hop_1, hop_2,
                                    destination, currency, logger)
                        path_list.append(path)
                        logger.debug('Path Found: {}->{}({}) --> {}->{}({})'
                                     .format(trade_1.sell_coin.id,
                                             trade_1.buy_coin.id,
                                             exch_A.exchange.id,
                                             trade_2.sell_coin.id,
                                             trade_2.buy_coin.id,
                                             exch_B.exchange.id))
    logger.info("End of '3. INDIRECT EXCHANGE(TWO HOPS)'")

    # generate_paths_file(path_list, currency, logger)
    logger.info("Path calculation finished. '{}' results"
                .format(len(path_list)))
    return path_list
