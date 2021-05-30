import datetime
import math
import traceback
from secrets import token_hex
from flask import (render_template, url_for, redirect, request, make_response,
                   current_app, Markup, send_from_directory)
from flask_blogging.views import _get_blogging_engine
from crypto_exchange_path import app, db, mail
from crypto_exchange_path.config import Params
from crypto_exchange_path.forms import SearchForm, FeedbackForm, PromoForm
from crypto_exchange_path.path_calculator import calc_paths
from crypto_exchange_path.utils import (set_logger,
                                        error_notifier,
                                        feedback_notifier,
                                        warning_notifier,
                                        get_meta_tags,
                                        get_exch_text,
                                        load_json_file,
                                        get_coin_data,
                                        get_exchange_data,
                                        round_number,
                                        round_big_number)
from crypto_exchange_path.utils_db import (get_exch_by_name,
                                           get_exchanges,
                                           get_coin_by_longname,
                                           get_coin,
                                           get_exchange,
                                           fx_exchange,
                                           get_trading_fees_by_exch,
                                           get_dep_with_fees_by_exch,
                                           get_coin_fees,
                                           get_coins,
                                           get_promos,
                                           get_coin_by_urlname,
                                           get_coin_by_symbol,
                                           get_mapping)
from crypto_exchange_path.models import (Feedback,
                                         Subscriber)
from crypto_exchange_path.info_fetcher import (update_prices,
                                               update_pairs,
                                               import_exchanges,
                                               import_fees,
                                               import_coins,
                                               import_pairs,
                                               update_coins_info,
                                               update_people_info,
                                               update_tags_info)

# Start logging
logger = set_logger('Main', Params.LOGGER_DETAIL)

# Load information files
coin_info_file = load_json_file(Params.COIN_INFO_FILE, logger)
people_info_file = load_json_file(Params.PEOPLE_INFO_FILE, logger)
tag_info_file = load_json_file(Params.TAG_INFO_FILE, logger)
exchange_info_file = load_json_file(Params.EXCHANGE_INFO_FILE, logger)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


def manage_feedback_form(feedback_form, page):
    date = datetime.datetime.now()
    text = feedback_form.text.data
    if not text or len(text) == 0:
        return
    if len(text) > 500:
        text = text[0:500]
    if app.debug:
        status = 'Debug'
    else:
        status = 'Production'
    feedback = Feedback(datetime=date,
                        page=page,
                        text=text,
                        status=status)
    feedback_notifier(text, page, mail, logger)
    db.session.add(feedback)
    db.session.commit()


def manage_promo_form(promo_form, subscription):
    date = datetime.datetime.now()
    email = promo_form.email.data
    if app.debug:
        status = 'Debug'
    else:
        status = 'Production'
    subscriber = Subscriber(email=email,
                            subscription=subscription,
                            date=date,
                            status=status)
    db.session.add(subscriber)
    db.session.commit()


def get_latest_posts(tag=None, count=3):
    """ Gets the latest 'count' posts of the given tag.
    If no tag is given, it gets posts from any tag.
    Returns a list of posts objects.
    """
    blogging_engine = _get_blogging_engine(current_app)
    storage = blogging_engine.storage
    posts = storage.get_posts(count=count, offset=0, include_draft=False,
                              tag=tag, user_id=None, recent=True)
    for post in posts:
        blogging_engine.process_post(post, render=True)
    return posts


@app.route("/", methods=['GET', 'POST'])
def home():
    url_orig_coin = 'empty'
    url_dest_coin = 'empty'
    input_form = SearchForm()
    # If 'calc_currency' exists in cookie, use it
    currency = request.cookies.get('calc_currency')
    if currency:
        curr = currency
        input_form.currency.data = currency
    else:
        curr = Params.DEFAULT_CURRENCY
    curr = get_coin(curr)
    exchanges = get_exchanges(['Exchange'], status='Active')
    user_exchanges = [exch.id for exch in exchanges]
    # Get Blog information
    posts = get_latest_posts(None, 6)
    # Get Meta tags
    title = get_meta_tags('Home', 'Title')
    description = get_meta_tags('Home', 'Description')
    # Get forms
    feedback_form = FeedbackForm()
    promo_form = PromoForm()
    # Get promos
    promos = get_promos()
    # Actions if Feedback Form was filled
    if promo_form.promo_submit.data:
        if promo_form.validate():
            manage_promo_form(promo_form, 'Promos')
    # Actions if Feedback Form was filled
    if feedback_form.feedback_submit.data:
        if feedback_form.validate():
            manage_feedback_form(feedback_form, request.path)
    resp = make_response(render_template('home.html', form=input_form,
                                         curr=curr, exchanges=exchanges,
                                         user_exchanges=user_exchanges,
                                         title=title,
                                         description=description,
                                         feedback_form=feedback_form,
                                         promo_form=promo_form,
                                         promos=promos,
                                         url_orig_coin=url_orig_coin,
                                         url_dest_coin=url_dest_coin,
                                         add_flaticon_link=True,
                                         posts=posts))
    # Store session ID in cookie if it is not already stored
    session_id = request.cookies.get('session')
    if not session_id:
        resp.set_cookie('session', token_hex(8))
        session_id = request.cookies.get('session')
    return resp


@app.route("/exchanges", methods=['GET', 'POST'])
def exchanges():
    url_orig_coin = 'empty'
    url_dest_coin = 'empty'
    input_form = SearchForm()
    # If 'calc_currency' exists in cookie, use it
    currency = request.cookies.get('calc_currency')
    if currency:
        curr = currency
        input_form.currency.data = currency
    else:
        curr = Params.DEFAULT_CURRENCY
    curr = get_coin(curr)
    feedback_form = FeedbackForm()
    exchanges = get_exchanges(['Exchange'], status='Active')
    user_exchanges = [exch.id for exch in exchanges]
    # Get Blog information
    posts = get_latest_posts('Exchanges', 6)
    # Get Meta tags
    title = get_meta_tags('Exchanges', 'Title')
    description = get_meta_tags('Exchanges', 'Description')
    # Actions if Feedback Form was filled
    if feedback_form.feedback_submit.data:
        if feedback_form.validate():
            manage_feedback_form(feedback_form, request.path)
    resp = make_response(render_template('exchanges.html', form=input_form,
                                         curr=curr, exchanges=exchanges,
                                         user_exchanges=user_exchanges,
                                         title=title,
                                         description=description,
                                         feedback_form=feedback_form,
                                         url_orig_coin=url_orig_coin,
                                         url_dest_coin=url_dest_coin,
                                         posts=posts))
    # Store session ID in cookie if it is not already stored
    session_id = request.cookies.get('session')
    if not session_id:
        resp.set_cookie('session', token_hex(8))
        session_id = request.cookies.get('session')
    return resp


@app.route("/crypto-promotions", methods=['GET', 'POST'])
def promotions():
    try:
        # If 'calc_currency' exists in cookie, use it
        currency = request.cookies.get('calc_currency')
        if currency:
            curr = currency
        else:
            curr = Params.DEFAULT_CURRENCY
        curr = get_coin(curr)
        # Get forms
        feedback_form = FeedbackForm()
        promo_form = PromoForm()
        # Get Meta tags
        title = get_meta_tags('Promotions', 'Title')
        description = get_meta_tags('Promotions', 'Description')
        # Get promos
        promos = get_promos()
        # Actions if Feedback Form was filled
        if promo_form.promo_submit.data:
            if promo_form.validate():
                manage_promo_form(promo_form, 'Promos')
        # Actions if Feedback Form was filled
        if feedback_form.feedback_submit.data:
            if feedback_form.validate():
                manage_feedback_form(feedback_form, request.path)
    # Catch generic exception just in case anything went wront
    except Exception as e:
        logger.error("routes: Error procesing 'crypto-promotions'")
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return redirect(url_for('home'))
    # Load page
    return render_template('promotions.html',
                           curr=curr,
                           title=title,
                           description=description,
                           feedback_form=feedback_form,
                           promo_form=promo_form,
                           promos=promos)


@app.route("/exchanges/search/<url_orig_coin>-to-<url_dest_coin>",
           methods=['GET', 'POST'])
def exch_results(url_orig_coin=None, url_dest_coin=None):
    """There are two ways of landing in this page:
         - Search form was filled: performs search and returns results
         - Direct external link (no form was filled!): in this case,
         a page with no results is shown, and then from the page a proper
         calculation is triggered. It is done like this to let the user
         load the page as soon as possible.
    """
    try:
        session_id = request.cookies.get('session')
        if not session_id:
            new_session_id = token_hex(8)
        sorted_paths = []
        input_form = SearchForm()
        # Choose currency: 1) Form 2) Cookie 3) Default
        currency = request.cookies.get('calc_currency')
        if input_form.currency.data != 'Empty':
            curr = input_form.currency.data
        elif currency:
            curr = currency
            input_form.currency.data = curr
        else:
            curr = Params.DEFAULT_CURRENCY
            input_form.currency.data = curr
        curr = get_coin(curr)
        if not curr:
            curr = get_coin('usd-us-dollars')
        auto_search = False
        feedback_form = FeedbackForm()
        exchanges = get_exchanges(['Exchange'], status='Active')
        user_exchanges = [exch.id for exch in exchanges]
        path_results = None
        # Get Meta tags (in case form was not filled)
        title = get_meta_tags('Exchanges|Results',
                              'Title',
                              [url_orig_coin.upper(), url_dest_coin.upper()])
        description = get_meta_tags('Exchanges|Results',
                                    'Description',
                                    [url_orig_coin.upper(),
                                     url_dest_coin.upper()])
        # 1) ACTIONS IF *SEARCH* FORM WAS FILLED
        if input_form.search_submit.data:
            if input_form.validate():
                curr = input_form.currency.data
                curr = get_coin(curr)
                orig_loc = get_exch_by_name(input_form.orig_loc.data)
                orig_coin = get_coin_by_longname(input_form.orig_coin.data)
                # Save 'orig_amt' as Float or integer depending on value
                num = float(input_form.orig_amt.data)
                if num % 1 == 0:
                    num = int(num)
                orig_amt = num
                dest_loc = get_exch_by_name(input_form.dest_loc.data)
                dest_coin = get_coin_by_longname(input_form.dest_coin.data)
                user_exchanges = input_form.exchanges.data
                # Get Meta tags (again, if form was filled)
                title = get_meta_tags('Exchanges|Results',
                                      'Title',
                                      [orig_coin.symbol, dest_coin.symbol])
                description = get_meta_tags('Exchanges|Results',
                                            'Description',
                                            [orig_coin.long_name,
                                             dest_coin.long_name])
                # If user selected all Exchanges or none of them, don't filter
                if len(user_exchanges) == len(exchanges):
                    user_exchanges = []
                fee_settings = {"CEP": input_form.cep_promos.data,
                                "Default": input_form.default_fee.data,
                                "Binance": input_form.binance_fee.data}
                # start_time = datetime.datetime.now()
                try:
                    paths = calc_paths(orig_loc, orig_coin, orig_amt,
                                       dest_loc, dest_coin,
                                       curr, fee_settings, logger)
                    path_results = len(paths)
                # Catch generic exception if anything went wrong in logic
                except Exception as e:
                    db.session.rollback()
                    error_notifier(type(e).__name__,
                                   traceback.format_exc(),
                                   mail,
                                   logger)
                    paths = []
                    path_results = -1
                # If no results were found, check "orign_amt" to try again
                if path_results == 0:
                    amount_usd = fx_exchange(orig_coin.id,
                                             'usd-us-dollars',
                                             orig_amt,
                                             logger)
                    if amount_usd < 20:
                        orig_amt = round_number(orig_amt * 20 / amount_usd)
                        orig_amt = round_big_number(orig_amt)
                        input_form.orig_amt.data = orig_amt
                        try:
                            paths = calc_paths(orig_loc, orig_coin, orig_amt,
                                               dest_loc, dest_coin,
                                               curr, fee_settings, logger)
                            path_results = len(paths)
                        # Catch generic exception if anything went wrong
                        except Exception as e:
                            db.session.rollback()
                            error_notifier(type(e).__name__,
                                           traceback.format_exc(),
                                           mail,
                                           logger)
                            paths = []
                            path_results = -1
                # If no results were found, send worning email
                if path_results == 0:
                    args_dic = {"orig_amt": orig_amt,
                                "orig_coin": orig_coin.id,
                                "orig_loc": orig_loc.id,
                                "dest_coin": dest_coin.id,
                                "dest_loc": dest_loc.id,
                                "currency": curr.id}
                    warning_notifier("Search with no results",
                                     args_dic,
                                     mail,
                                     logger)
                # Select all Exchanges if no partial selection was made
                if not user_exchanges:
                    user_exchanges = [exch.id for exch in exchanges]
                # Return capped list of results
                sorted_paths = sorted(paths, key=lambda x: x.total_fees)
                sorted_paths = sorted_paths[0:Params.MAX_PATHS]
        # 2) ACTIONS IF *NO* FORM WAS FILLED (DIRECT LINK!)
        else:
            orig_coin = get_coin_by_symbol(url_orig_coin.upper())
            dest_coin = get_coin_by_symbol(url_dest_coin.upper())
            # If 'orig_coin' or 'dest_coin' not found, try in mappings table
            if not orig_coin:
                new_symbol = get_mapping('Coin',
                                         'symbol',
                                         url_orig_coin.upper())
                if new_symbol:
                    orig_coin = get_coin_by_symbol(new_symbol)
            if not dest_coin:
                new_symbol = get_mapping('Coin',
                                         'symbol',
                                         url_dest_coin.upper())
                if new_symbol:
                    dest_coin = get_coin_by_symbol(new_symbol)
            # Procced with function
            if orig_coin:
                input_form.orig_coin.data = orig_coin.long_name
                amt = fx_exchange('usd-us-dollars', orig_coin.id, 3000, logger)
                if amt:
                    amt = round_big_number(amt)
                    input_form.orig_amt.data = str(math.ceil(amt)) + " "
            if dest_coin:
                input_form.dest_coin.data = dest_coin.long_name
            auto_search = True
        # Actions if Feedback Form was filled
        if feedback_form.feedback_submit.data:
            if feedback_form.validate():
                manage_feedback_form(feedback_form, request.path)
    # Catch generic exception just in case anything went wront in logic
    except Exception as e:
        db.session.rollback()
        logger.error("Routes: Non-handled exception at '{}'"
                     .format(request.url))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return redirect(url_for('exchanges'))
    resp = make_response(render_template('exch_results.html',
                                         form=input_form,
                                         curr=curr,
                                         exchanges=exchanges,
                                         user_exchanges=user_exchanges,
                                         paths=sorted_paths,
                                         path_results=path_results,
                                         auto_search=auto_search,
                                         feedback_form=feedback_form,
                                         title=title,
                                         description=description,
                                         url_orig_coin=url_orig_coin,
                                         url_dest_coin=url_dest_coin))
    # Store session ID & Currency in cookie if there are not already stored
    if not session_id:
        resp.set_cookie('session', new_session_id)
    if currency != curr.id:
        resp.set_cookie('calc_currency', curr.id)
    return resp


@app.route("/exchanges/search/<url_orig_coin>+<url_dest_coin>",
           methods=['GET', 'POST'])
def exch_results_old_1a(url_orig_coin=None, url_dest_coin=None):
    """Redirect for Old format results (1)
    """
    return redirect(url_for('exch_results',
                            url_orig_coin=url_orig_coin.lower(),
                            url_dest_coin=url_dest_coin.lower()))


@app.route("/exchanges/result/<url_orig_coin>+<url_dest_coin>",
           methods=['GET', 'POST'])
def exch_results_old_1b(url_orig_coin=None, url_dest_coin=None):
    """Redirect for Old format results (1)
    """
    return redirect(url_for('exch_results',
                            url_orig_coin=url_orig_coin.lower(),
                            url_dest_coin=url_dest_coin.lower()))


@app.route("/exchanges/search/<url_orig_coin>/<url_dest_coin>",
           methods=['GET', 'POST'])
def exch_results_old_2(url_orig_coin=None, url_dest_coin=None):
    """Redirect for Old format results (2)
    """
    return redirect(url_for('exch_results',
                            url_orig_coin=url_orig_coin.lower(),
                            url_dest_coin=url_dest_coin.lower()))


@app.route("/exchanges/fees", methods=['GET', 'POST'])
def exchange_fees_exch():
    """'Exchange fees by exchange' page.
    """
    # If 'calc_currency' exists in cookie, use it
    currency = request.cookies.get('calc_currency')
    if currency:
        curr = currency
    else:
        curr = Params.DEFAULT_CURRENCY
    curr = get_coin(curr)
    feedback_form = FeedbackForm()
    # Get exchanges
    exchanges = get_exchanges(['Exchange'], status='Active')
    # Get Meta tags
    title = get_meta_tags('Exchanges|Fees|Exch',
                          'Title')
    description = get_meta_tags('Exchanges|Fees|Exch',
                                'Description')
    # Actions if Feedback Form was filled
    if feedback_form.feedback_submit.data:
        if feedback_form.validate():
            manage_feedback_form(feedback_form, request.path)
    return render_template('exchange_fees_exch.html',
                           curr=curr,
                           title=title,
                           description=description,
                           feedback_form=feedback_form,
                           exchanges=exchanges)


@app.route("/exchanges/fees/coins", methods=['GET', 'POST'])
def exchange_fees_coin():
    """'Exchange fees by cryptocurrency' page.
    """
    # If 'calc_currency' exists in cookie, use it
    currency = request.cookies.get('calc_currency')
    if currency:
        curr = currency
    else:
        curr = Params.DEFAULT_CURRENCY
    curr = get_coin(curr)
    feedback_form = FeedbackForm()
    # Get exchanges
    coins = get_coins(pos_limit=Params.BROWSE_FEE_COINS, status="Active")
    # Get Meta tags
    title = get_meta_tags('Exchanges|Fees|Coin',
                          'Title')
    description = get_meta_tags('Exchanges|Fees|Coin',
                                'Description')
    # Actions if Feedback Form was filled
    if feedback_form.feedback_submit.data:
        if feedback_form.validate():
            manage_feedback_form(feedback_form, request.path)
    # Load page
    return render_template('exchange_fees_coin.html',
                           curr=curr,
                           title=title,
                           description=description,
                           feedback_form=feedback_form,
                           coins=coins)


@app.route("/exchanges/fees/<exch_id>", methods=['GET', 'POST'])
def exchange_fees_by_exch(exch_id):
    """Displays the fees of the exchange given as argument.
    """
    exchange = get_exchange(exch_id)
    # If exchange not recognnized, redirect
    if not exchange:
        return redirect(url_for('exchange_fees_exch'))
    # Get Exchange fees
    trading_fees = get_trading_fees_by_exch(exch_id)
    dep_with_fees = get_dep_with_fees_by_exch(exch_id)
    # Get Exchange data
    exch_data = get_exchange_data(exchange.id,
                                  exchange.site_url,
                                  exchange_info_file,
                                  logger)
    # Get promos
    promos = get_promos(exchange.id)
    # If 'calc_currency' exists in cookie, use it
    currency = request.cookies.get('calc_currency')
    if currency:
        curr = currency
    else:
        curr = Params.DEFAULT_CURRENCY
    curr = get_coin(curr)
    # Get forms
    feedback_form = FeedbackForm()
    promo_form = PromoForm()
    # Get Meta tags
    title = get_meta_tags('Exchanges|Fees|Exch|Exch',
                          'Title',
                          [exchange.name])
    description = get_meta_tags('Exchanges|Fees|Exch|Exch',
                                'Description',
                                [exchange.name])
    # Get Texts
    trading_text = Markup(get_exch_text(exch_id, 'Trade'))
    withdrawal_text = Markup(get_exch_text(exch_id, 'Withdrawal'))
    # Actions if Feedback Form was filled
    if feedback_form.feedback_submit.data:
        if feedback_form.validate():
            manage_feedback_form(feedback_form, request.path)
    # Load page
    return render_template('exchange_fees_by_exch.html',
                           exchange=exchange,
                           curr=curr,
                           title=title,
                           description=description,
                           feedback_form=feedback_form,
                           promo_form=promo_form,
                           trading_text=trading_text,
                           withdrawal_text=withdrawal_text,
                           trading_fees=trading_fees,
                           dep_with_fees=dep_with_fees,
                           exch_data=exch_data,
                           promos=promos)


@app.route("/exchanges/fees/<exch_id>-fees", methods=['GET', 'POST'])
def exchange_fees_by_exch_old(exch_id):
    """Redirect for Old format url
    """
    return redirect(url_for('exchange_fees_exch'))


@app.route("/exchanges/fees/coins/<coin_url_name>", methods=['GET', 'POST'])
def exchange_fees_by_coin(coin_url_name):
    """Displays the fees for the coin given as as argument.
    """
    try:
        coin = get_coin_by_urlname(coin_url_name)
        # If coin not recognized, redirect
        if not coin:
            new_url = get_mapping('Coin', 'url_name', coin_url_name)
            if new_url:
                return redirect(url_for('exchange_fees_by_coin',
                                        coin_url_name=new_url))
            else:
                return redirect(url_for('exchange_fees_coin'))
        # Get coin fees
        coin_fees = get_coin_fees(coin.id)
        # Get coin data
        coin_data = get_coin_data(coin.id,
                                  coin_info_file,
                                  people_info_file,
                                  tag_info_file,
                                  logger)
        # If 'calc_currency' exists in cookie, use it
        currency = request.cookies.get('calc_currency')
        if currency:
            curr = currency
        else:
            curr = Params.DEFAULT_CURRENCY
        curr = get_coin(curr)
        # Get forms
        feedback_form = FeedbackForm()
        promo_form = PromoForm()
        # Get Meta tags
        title = get_meta_tags('Exchanges|Fees|Coin|Coin',
                              'Title',
                              [coin.long_name])
        description = get_meta_tags('Exchanges|Fees|Coin|Coin',
                                    'Description',
                                    [coin.long_name,
                                     coin.long_name,
                                     coin.symbol])
        # Get search coins
        if (coin.type == 'Crypto'):
            quick_search_coins = Params.QUICK_SEARCH_COINS['Crypto']
        else:
            quick_search_coins = Params.QUICK_SEARCH_COINS['Fiat']
        search_coins = []
        search_count = 0
        for item in quick_search_coins:
            if item != coin.id:
                coinA = get_coin(item)
                search_coins.append({"coinA": coinA, "coinB": coin})
                search_count += 1
            # If for items have been gathered, exit loop
            if search_count == 4:
                break
        # Get promos
        promos = get_promos()
        # Actions if Feedback Form was filled
        if promo_form.promo_submit.data:
            if promo_form.validate():
                manage_promo_form(promo_form, 'Promos')
        # Actions if Feedback Form was filled
        if feedback_form.feedback_submit.data:
            if feedback_form.validate():
                manage_feedback_form(feedback_form, request.path)
    # Catch generic exception just in case anything went wront
    except Exception as e:
        logger.error("routes: Error procesing '{}'".format(coin_url_name))
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return redirect(url_for('exchange_fees_coin'))
    # Load page
    return render_template('exchange_fees_by_coin.html',
                           coin=coin,
                           coin_data=coin_data,
                           curr=curr,
                           title=title,
                           description=description,
                           feedback_form=feedback_form,
                           promo_form=promo_form,
                           coin_fees=coin_fees,
                           search_coins=search_coins,
                           promos=promos)


@app.route("/exchanges/fees/coin/<coin_url_name>-fees",
           methods=['GET', 'POST'])
def exchange_fees_by_coin_old(coin_url_name):
    """Redirect for Old format url
    """
    return redirect(url_for('exchange_fees_coin'))


""" ***********************************************************************
***************************************************************************
Sitemap & Robots files
***************************************************************************
*********************************************************************** """


@app.route('/robots.txt')
@app.route('/sitemap.txt')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


""" ***********************************************************************
***************************************************************************
Routes to trigger processes
***************************************************************************
*********************************************************************** """


@app.route("/update/prices_slfjh23hk353mh4567df")
def update_prcs():
    try:
        update_prices(logger)
        return "ok"
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()


@app.route("/update/pairs_rqoewirhkfldajvczmcxzvf")
def update_pairs_route():
    try:
        update_pairs(logger)
        return "ok"
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()


@app.route("/import/exchanges_amnsdfno8234q8rfafonfd")
def import_exchanges_route():
    try:
        import_exchanges(logger, Params.EXCHANGES_PATH)
        return "ok"
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()


@app.route("/import/fees_amnsdfno8234q8rfafonfd")
def import_fees_route():
    try:
        import_fees(logger, Params.FEES_PATH)
        return "ok"
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()


@app.route("/import/coins_amnsdfno8234q8rfafonfd")
def import_coins_route():
    try:
        import_coins(logger, Params.COINS_PATH)
        return "ok"
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()


@app.route("/import/pairs_amnsdfno8234q8rfafonfd")
def import_pairs_route():
    try:
        import_pairs(logger, Params.PAIRS_PATH)
        return "ok"
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()


@app.route("/get/coin_info_dfaadsfbdsabyqbedzc")
def get_coin_info():
    global coin_info_file
    try:
        exit_code = update_coins_info(logger)
        coin_info_file = load_json_file(Params.COIN_INFO_FILE, logger)
        return str(exit_code)
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()


@app.route("/get/people_info_vzcadsgjgqeuureed")
def get_people_info():
    global people_info_file
    try:
        exit_code = update_people_info(logger)
        people_info_file = load_json_file(Params.PEOPLE_INFO_FILE, logger)
        return str(exit_code)
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()


@app.route("/get/tag_info_uoruyrweqryqzmcxvnds")
def get_tag_info():
    global tag_info_file
    try:
        exit_code = update_tags_info(logger)
        tag_info_file = load_json_file(Params.TAG_INFO_FILE, logger)
        return str(exit_code)
    except Exception as e:
        error_notifier(type(e).__name__,
                       traceback.format_exc(),
                       mail,
                       logger)
        return traceback.format_exc()
