from flask_wtf import FlaskForm
from wtforms import (StringField, SubmitField, TextAreaField, SelectField,
                     RadioField, SelectMultipleField)
from wtforms.validators import (DataRequired, ValidationError, Email)
from crypto_exchange_path.config import Params
from crypto_exchange_path.utils_db import (get_coins,
                                           get_exch_by_coin,
                                           get_exchange_choices,
                                           get_currency_choices,
                                           get_coin_by_longname,
                                           get_exch_by_name,
                                           set_default_exch,
                                           get_exchange,
                                           get_subscriber)
from crypto_exchange_path.utils import is_number


class SearchForm(FlaskForm):

    currency = SelectField('Currency',
                           choices=get_currency_choices(),
                           validators=[DataRequired()],
                           default='Empty')
    orig_amt = StringField('Origin amount')
    orig_coin = StringField('Origin coin')
    orig_loc = StringField('Origin location')
    dest_coin = StringField('Destination coin')
    dest_loc = StringField('Destination location')
    connection_type = SelectField('Connections',
                                  choices=Params.CONNECTIONS_CHOICES,
                                  validators=[DataRequired()],
                                  default='2')
    exchanges = SelectMultipleField('Exchanges',
                                    choices=get_exchange_choices(['Exchange']),
                                    default=[exch[0] for exch in
                                             get_exchange_choices(
                                             ['Exchange'])])
    cep_promos = RadioField('CEP promos',
                            choices=Params.CEP_CHOICES,
                            default='(CEP)')
    # default_fee = RadioField('Default fee',
    #                          choices=Params.TRADE_FEE_CHOICES,
    #                          default='(Avg)')
    default_fee = SelectField('Default fee',
                              choices=Params.TRADE_FEE_CHOICES,
                              validators=[DataRequired()],
                              default='(Avg)')
    binance_fee = RadioField('Binance fees',
                             choices=[('(BNB)', 'Pay fees in BNB (0.075%)'),
                                      ('(No-BNB)', 'Regular fees (0.1%)')],
                             default='(BNB)')
    search_submit = SubmitField("Go!")

    def validate_orig_amt(self, orig_amt):
        if not orig_amt.data:
            raise ValidationError("Please, fill 'Amount'")
        if not is_number(orig_amt.data):
            raise ValidationError("Not a number")
        elif float(orig_amt.data) <= 0:
            raise ValidationError("Amount must be a positive number")

    def validate_orig_coin(self, orig_coin):
        if not orig_coin.data:
            raise ValidationError("Please, fill 'Coin'")
        else:
            coin = get_coin_by_longname(orig_coin.data)
            if coin:
                coin = coin.id
            coins = get_coins(status='Active', return_ids=True)
            if coin not in coins:
                raise ValidationError("Unknown coin")

    def validate_orig_loc(self, orig_loc):
        coin = get_coin_by_longname(self.orig_coin.data)
        if coin:
            valid_coins = get_coins(status='Active', return_ids=True)
            # Only raise error is 'orig_coin' exist
            if coin.id in valid_coins:
                # If valid coin but no exchange, set default exchange
                if not orig_loc.data or orig_loc.data in ['(Default)',
                                                          'Wallet',
                                                          'Bank']:
                    self.orig_loc.data = set_default_exch(coin.id)
                    return
                valid_exchs = get_exch_by_coin(coin.id)
                exch_id = get_exch_by_name(orig_loc.data)
                if exch_id:
                    exch_id = exch_id.id
                else:
                    # Check if extra characters where added
                    for valid_exch in valid_exchs:
                        exch_desc = get_exchange(valid_exch).name
                        if orig_loc.data.find(exch_desc) >= 0:
                            self.orig_loc.data = exch_desc
                            return
                    # raise ValidationError("'{}' is not a valid exchange name"
                    #                       .format(orig_loc.data))
                # Check that exchange is valid
                if exch_id not in valid_exchs:
                    # If not valid, use default exchange
                    self.orig_loc.data = set_default_exch(coin.id)
                    # raise ValidationError("'{}' not available in '{}'"
                    #                       .format(coin.id, orig_loc.data))

    def validate_dest_coin(self, dest_coin):
        if not dest_coin.data:
            raise ValidationError("Please, fill 'Coin'")
        else:
            coin = get_coin_by_longname(dest_coin.data)
            if coin:
                coin = coin.id
            coins = get_coins(status='Active', return_ids=True)
            if coin not in coins:
                raise ValidationError("Unknown coin")
            elif (dest_coin.data == self.orig_coin.data):
                raise ValidationError("Same origin and destination coin")

    def validate_dest_loc(self, dest_loc):
        coin = get_coin_by_longname(self.dest_coin.data)
        if coin:
            valid_coins = get_coins(status='Active', return_ids=True)
            # Only raise error is 'dest_coin' exist
            if coin.id in valid_coins:
                # If valid coin but no exchange, set default exchange
                if not dest_loc.data or dest_loc.data in ['(Default)',
                                                          'Wallet',
                                                          'Bank']:
                    self.dest_loc.data = set_default_exch(coin.id)
                    return
                valid_exchs = get_exch_by_coin(coin.id)
                exch_id = get_exch_by_name(dest_loc.data)
                if exch_id:
                    exch_id = exch_id.id
                else:
                    # Check if extra characters where added
                    for valid_exch in valid_exchs:
                        exch_desc = get_exchange(valid_exch).name
                        if dest_loc.data.find(exch_desc) >= 0:
                            self.dest_loc.data = exch_desc
                            return
                    # raise ValidationError("'{}' is not a valid exchange name"
                    #                       .format(dest_loc.data))
                # Check that exchange is valid
                if exch_id not in valid_exchs:
                    # If not valid, use default exchange
                    self.dest_loc.data = set_default_exch(coin.id)
                    # raise ValidationError("'{}' not available in '{}'"
                    #                       .format(coin.id, dest_loc.data))


class FeedbackForm(FlaskForm):
    text = TextAreaField('Detail',
                         filters=[lambda x: x or None])
    feedback_submit = SubmitField('Send feedback')


class PromoForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    promo_submit = SubmitField('Get alerts')

    def validate_email(self, email):
        email = get_subscriber(email.data, 'Promos')
        if email:
            raise ValidationError("Email already registered")
