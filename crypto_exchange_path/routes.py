import datetime
from secrets import token_hex
from flask import render_template, url_for, redirect
from crypto_exchange_path import app, db
from crypto_exchange_path.config import Params
from crypto_exchange_path.forms import SearchForm, FeedbackForm
from crypto_exchange_path.path_calculator import calc_paths
from crypto_exchange_path.utils import set_logger
from crypto_exchange_path.utils_db import (get_exchange, get_exchanges,
                                           get_coin_by_longname)
from crypto_exchange_path.models import Feedback, QueryRegister

# Start logging
logger = set_logger('Main', 'INFO')


@app.route("/", methods=['GET', 'POST'])
@app.route("/<session_id>", methods=['GET', 'POST'])
def main(session_id=None):
    if not session_id or len(session_id) != 32:
        session_id = token_hex(16)
    sorted_paths = []
    input_form = SearchForm()
    feedback_form = FeedbackForm()
    exchanges = get_exchanges('Exchange')
    user_exchanges = exchanges
    gen_wallet = Params.GENERIC_WALLET
    curr = Params.DEFAULT_CURRENCY
    path_results = -1
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
        paths = calc_paths(orig_loc, orig_coin, orig_amt,
                           dest_loc, dest_coin, connection_type,
                           user_exchanges, curr, fee_settings, logger)
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
        db.session.add(query)
        db.session.commit()
        # Select all Exchanges if no partial selection was made
        if not user_exchanges:
            user_exchanges = exchanges
        # Return capped list of results
        sorted_paths = sorted(paths, key=lambda x: x.total_fees)
        sorted_paths = sorted_paths[0:Params.MAX_PATHS]
        path_results = len(paths)
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
            return redirect(url_for('main'))
    return render_template('main.html', form=input_form, curr=curr,
                           exchanges=exchanges, user_exchanges=user_exchanges,
                           paths=sorted_paths, gen_wallet=gen_wallet,
                           path_results=path_results,
                           feedback_form=feedback_form,
                           open_feedback_modal=open_feedback_modal,
                           session_id=session_id)


@app.route("/landing")
def landing():
    return render_template('landing_page.html', title='Test')


@app.route("/start")
def start():
    return render_template('start.html', title='Test')
