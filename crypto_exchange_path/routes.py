import datetime
import math
import traceback
from secrets import token_hex
from flask import render_template, url_for, redirect
from crypto_exchange_path import app, db, mail
from crypto_exchange_path.config import Params
from crypto_exchange_path.forms import SearchForm, FeedbackForm
from crypto_exchange_path.path_calculator import calc_paths
from crypto_exchange_path.utils import set_logger, error_notifier
from crypto_exchange_path.utils_db import (get_exchange, get_exchanges,
                                           get_coin_by_longname, get_coin,
                                           fx_exchange)
from crypto_exchange_path.models import Feedback, QueryRegister
from crypto_exchange_path.info_fetcher import update_prices

# Start logging
logger = set_logger('Main', 'INFO')


def manage_feedback_form(feedback_form):
    date = datetime.datetime.now()
    topic = feedback_form.topic.data
    subject = feedback_form.subject.data
    detail = feedback_form.detail.data
    feedback = Feedback(datetime=date,
                        topic=topic,
                        subject=subject,
                        detail=detail)
    db.session.add(feedback)
    db.session.commit()


@app.route("/", methods=['GET', 'POST'])
@app.route("/exchanges/<session_id>&currency=<currency>",
           methods=['GET', 'POST'])
@app.route("/exchanges", methods=['GET', 'POST'])
@app.route("/exchanges/<session_id>", methods=['GET', 'POST'])
def exchanges(session_id=None, currency=None):
    if not session_id or len(session_id) != 32:
        session_id = token_hex(16)
    input_form = SearchForm()
    # If 'currency' was provided, use it
    if currency:
        curr = currency
        input_form.currency.data = currency
    else:
        curr = Params.DEFAULT_CURRENCY
    feedback_form = FeedbackForm()
    exchanges = get_exchanges('Exchange')
    user_exchanges = exchanges
    open_feedback_modal = False
    # Actions if Feedback Form was filled
    if feedback_form.feedback_submit.data:
        # If form was filled, but with errors, open modal again
        open_feedback_modal = True
        if feedback_form.validate():
            # If form was properly filled, close modal again
            open_feedback_modal = False
            manage_feedback_form(feedback_form)
            return redirect(url_for('exchanges'))
    return render_template('exchanges.html', form=input_form, curr=curr,
                           exchanges=exchanges, user_exchanges=user_exchanges,
                           session_id=session_id,
                           feedback_form=feedback_form,
                           open_feedback_modal=open_feedback_modal)


@app.route("/exchanges/results/<session_id>&currency=<currency>/"
           "<orig_coin>&<dest_coin>", methods=['GET', 'POST'])
@app.route("/exchanges/results/<session_id>&currency=<currency>",
           methods=['GET', 'POST'])
@app.route("/exchanges/results/<session_id>", methods=['GET', 'POST'])
def exch_results(session_id=None, currency=None,
                 orig_coin=None, dest_coin=None):
    if not session_id or len(session_id) != 32:
        session_id = token_hex(16)
    sorted_paths = []
    input_form = SearchForm()
    # If 'currency' was provided, use it
    if currency:
        curr = currency
        input_form.currency.data = currency
    else:
        curr = Params.DEFAULT_CURRENCY
    # If 'orig_coin' and 'dest_coin' where provided, fill form
    auto_search = False
    if orig_coin and dest_coin:
        orig_coin = get_coin(orig_coin)
        dest_coin = get_coin(dest_coin)
        if orig_coin and dest_coin:
            input_form.orig_coin.data = orig_coin.long_name
            input_form.dest_coin.data = dest_coin.long_name
            amt = fx_exchange("USD", orig_coin.id, 3000, logger)
            input_form.orig_amt.data = str(math.ceil(amt))
            auto_search = True
    feedback_form = FeedbackForm()
    exchanges = get_exchanges('Exchange')
    user_exchanges = exchanges
    path_results = None
    open_feedback_modal = False
    # Actions if Search Form was filled
    if input_form.search_submit.data and input_form.validate():
        curr = input_form.currency.data
        orig_loc = get_exchange(input_form.orig_loc.data)
        orig_coin = get_coin_by_longname(input_form.orig_coin.data)
        orig_amt = float(input_form.orig_amt.data)
        dest_loc = get_exchange(input_form.dest_loc.data)
        dest_coin = get_coin_by_longname(input_form.dest_coin.data)
        connection_type = input_form.connection_type.data
        user_exchanges = input_form.exchanges.data
        # If user selected all Exchanges or none of them, don't filter
        if len(user_exchanges) == len(exchanges):
            user_exchanges = []
        fee_settings = {"CEP": input_form.cep_promos.data,
                        "Default": input_form.default_fee.data,
                        "Binance": input_form.binance_fee.data}
        start_time = datetime.datetime.now()
        try:
            paths = calc_paths(orig_loc, orig_coin, orig_amt,
                               dest_loc, dest_coin, connection_type,
                               user_exchanges, curr, fee_settings, logger)
            path_results = len(paths)
        # Catch generic exception just in case anything went wront in logic
        except Exception as e:
            error_notifier(type(e).__name__,
                           traceback.format_exc(),
                           mail,
                           logger)
            paths = []
            path_results = -1
        # Register query
        finish_time = datetime.datetime.now()
        results = len(paths)
        exchs = ""
        for exch in user_exchanges:
            exchs += exch + '|'
        exchs = exchs[:-1]
        query = QueryRegister(session_id=session_id,
                              orig_amt=orig_amt,
                              orig_coin=orig_coin.id,
                              orig_loc=orig_loc.id,
                              dest_coin=dest_coin.id,
                              dest_loc=dest_loc.id,
                              currency=curr,
                              connection_type=connection_type,
                              exchanges=exchs,
                              results=results,
                              start_time=start_time,
                              finish_time=finish_time)
        try:
            db.session.add(query)
            db.session.commit()
        except Exception as e:
            error_notifier(type(e).__name__,
                           traceback.format_exc(),
                           mail,
                           logger)
        # Select all Exchanges if no partial selection was made
        if not user_exchanges:
            user_exchanges = exchanges
        # Return capped list of results
        sorted_paths = sorted(paths, key=lambda x: x.total_fees)
        sorted_paths = sorted_paths[0:Params.MAX_PATHS]
    # Actions if Feedback Form was filled
    elif feedback_form.feedback_submit.data:
        # If form was filled, but with errors, open modal again
        open_feedback_modal = True
        if feedback_form.validate():
            open_feedback_modal = False
            date = datetime.datetime.now()
            topic = feedback_form.topic.data
            subject = feedback_form.subject.data
            detail = feedback_form.detail.data
            feedback = Feedback(datetime=date,
                                topic=topic,
                                subject=subject,
                                detail=detail)
            db.session.add(feedback)
            db.session.commit()
            return redirect(url_for('exch_results'))
    return render_template('exch_results.html', form=input_form, curr=curr,
                           exchanges=exchanges, user_exchanges=user_exchanges,
                           paths=sorted_paths, session_id=session_id,
                           path_results=path_results, auto_search=auto_search,
                           feedback_form=feedback_form,
                           open_feedback_modal=open_feedback_modal)


@app.route("/update/slfjh23hk353mh4567df")
def update_prcs():
    try:
        update_prices(logger)
        return "ok"
    except Exception as e:
        return traceback.format_exc()


@app.route("/landing")
def landing():
    return render_template('landing_page.html', title='Test')


@app.route("/start")
def start():
    return render_template('start.html', title='Test')
