# -*- coding: utf-8 -*-

import logging

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_round
from odoo.addons.payment.controllers.portal import PaymentProcessing

_logger = logging.getLogger(__name__)

try:
    import stripe
except ImportError:
    _logger.error('Odoo module payment_stripe_recurring_acs depends on the stripe python module')
    stripe = None


class Subscription(models.Model):
    _inherit = "sale.order"

    stripe_subscription_ref = fields.Char("Stripe Subscription Reference", copy=False)
    payment_token_id = fields.Many2one('payment.token', string="Token", help="Token for recurring payment")
    payment_provider = fields.Selection(related="subscription_payment_acquirer_id.provider", string="provider")

    def ir_cron_check_subscription_status(self):
        subscription_ids = self.search([('stripe_subscription_ref', '!=', False),('is_subscription_order','=', True),('subscription_state', '=', 'running')])
        for subscription_id in subscription_ids:
            acquirer_id = subscription_id.subscription_payment_acquirer_id
            if acquirer_id:
                stripe.api_key = acquirer_id.stripe_secret_key
                stripe_subscription = stripe.Subscription.retrieve(subscription_id.stripe_subscription_ref)
                if stripe_subscription.get('id') and stripe_subscription.get('status') == 'active' \
                    and subscription_id.subscription_state != 'running' and stripe_subscription.get('id') == subscription_id.stripe_subscription_ref:
                    stripe_subscription.delete()
                    subscription_id.update({'subscription_notes': "Your stripe subscription is inactive because invoice subscription is cancelled."})
                elif stripe_subscription.get('id') and stripe_subscription.get('status') == 'canceled' \
                    and subscription_id.subscription_state == 'running' and stripe_subscription.get('id') == subscription_id.stripe_subscription_ref:
                    subscription_id.update({'state': 'cancel', 'subscription_notes': "Your invoice subscription is cancel because stripe subscription isn't active."})
            else:
                raise ValidationError(_("Please configure your Stripe account !!"))

    def _get_stripe_subscription(self):
        self.ensure_one()
        acquirer_id = self.subscription_payment_acquirer_id
        order = self
        if order.payment_provider == 'stripe' and order.stripe_subscription_ref:   
            stripe.api_key = acquirer_id.stripe_secret_key
            stripe_subscription = stripe.Subscription.retrieve(order.stripe_subscription_ref)
            return stripe_subscription
        return False

    def action_subscription_cancel(self):
        for rec in self.filtered(lambda s: s.payment_token_id and s.stripe_subscription_ref):
            stripe_subscription = rec._get_stripe_subscription()
            stripe_subscription.delete()
            rec.update({'subscription_note': "Your stripe subscription is inactive because invoice subscription is cancelled."})
        return super(Subscription, self).action_subscription_cancel()

    def action_show_subscription_info(self):
        self.ensure_one()
        order = self
        if order.payment_provider == 'stripe':
            stripe_subscription = self._get_stripe_subscription()
            _logger.info("Stripe Subscription DATA: %s" % stripe_subscription)
    
    def action_get_latest_invoice(self):
        self.ensure_one()
        order = self
        if order.payment_provider == 'stripe':   
            stripe_subscription = self._get_stripe_subscription()
            latest_invoice = stripe.Invoice.retrieve(stripe_subscription['latest_invoice'])
            if latest_invoice:
                datetime_obj = datetime.fromtimestamp(latest_invoice.get('effective_at', False))
                if datetime_obj:
                    # Format datetime object as a string
                    formatted_date = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
                
                    _logger.info("Stripe Lastest invoice (%s): %s" % (formatted_date, latest_invoice))
                else:
                    _logger.info("Stripe Lastest invoice: %s" % latest_invoice)



class Schedule(models.Model):
    _inherit = "sale.subscription.schedule"


    @api.model
    def process_payment(self, invoice):
        invoice = super(Schedule, self).process_payment(invoice)
        self.ensure_one()
        order = self.order_id
        acquirer_id = order.subscription_payment_acquirer_id
        if order.payment_provider == 'stripe':
            stripe.api_key = acquirer_id.stripe_secret_key
            if not order.stripe_subscription_ref:
                if order.payment_token_id and acquirer_id and acquirer_id.provider == 'stripe':
                    try:
                        interval = order.subscription_type.unit if order.subscription_type.unit else ''
                        product = stripe.Product.create(name=order.name, type='service')
                        amount = str(int(float_round(sum(order.order_line.filtered(lambda o: o.product_id.subscription_ok == True).mapped('price_total')) * 100, 2)))
                        nickname = str(order.name) + ' Plan'
                        plan = stripe.Plan.create(currency=order.currency_id.name, interval=interval, interval_count=order.subscription_type.interval, product=product.get('id'), nickname=nickname, amount=amount)
                        stripe_subscription = stripe.Subscription.create(customer=order.payment_token_id.acquirer_ref, items=[{'plan': plan.get('id')}], off_session=True)
                        tx = invoice._create_payment_transaction({
                                'acquirer_id': acquirer_id.id,
                                'type': 'form',
                            })
                        if stripe_subscription.get('id') and stripe_subscription.get('status') == 'active' and stripe_subscription.get('latest_invoice'):
                            latest_invoice = stripe.Invoice.retrieve(stripe_subscription['latest_invoice'])
                            if latest_invoice.get('id') and latest_invoice.get('charge') and latest_invoice.get('status') == 'paid':
                                tx.write({
                                    'state': 'done',
                                    'date': fields.Datetime.now(),
                                    'acquirer_reference': latest_invoice['charge'],
                                    'payment_token_id': order.payment_token_id.id,
                                })
                                PaymentProcessing.add_payment_transaction(tx)
                                order.stripe_subscription_ref = stripe_subscription.get('id')
                                invoice.write({
                                    'stripe_invoice_ref': latest_invoice['id'],
                                })
                                tx._cron_post_process_after_done()
                                _logger.info('<%s> transaction <%s> completed, reconciled invoice %s (ID %s))',
                                                acquirer_id.provider, tx.id, invoice.name, invoice.id)
                            elif latest_invoice.get('id') and latest_invoice.get('status') != 'paid':
                                tx.write({
                                    'state': 'cancel',
                                    'state_message': latest_invoice.get('status'),
                                    'payment_token_id': subscription.payment_token_id.id,
                                })
                                _logger.info('<%s> transaction <%s> failed, reconciled invoice %s (ID %s))',
                                                acquirer_id.provider, tx.id, invoice.name, invoice.id)
                            else:
                                raise ValidationError(_("Stripe Invoice Charge Failed %s" % (latest_invoice.get('status'))))    
                        else:
                            raise ValidationError(_("Stripe Subscription Failed %s" % (stripe_subscription.get('status'))))
                    except ValidationError as e:
                        raise ValidationError(e.args[0])
                    except Exception as e:
                        raise UserError(_("Stripe Error! : %s !" % e))
            elif invoice.payment_state != 'paid':
                stripe_subscription = stripe.Subscription.retrieve(order.stripe_subscription_ref)
                if stripe_subscription.get('id') and stripe_subscription.get('status') == 'active' and stripe_subscription.get('latest_invoice'):
                    latest_invoice = stripe.Invoice.retrieve(stripe_subscription['latest_invoice'])
                    invoice.post()
                    tx = invoice._create_payment_transaction({
                        'acquirer_id': acquirer_id.id,
                        'type': 'form',
                    })
                    if latest_invoice.get('id') and latest_invoice.get('charge') and latest_invoice.get('status') == 'paid':
                        invoice.write({
                            'stripe_invoice_ref': latest_invoice['id'],
                        })
                        tx.write({
                            'state': 'done',
                            'date': fields.Datetime.now(),
                            'acquirer_reference': latest_invoice['charge'],
                            'payment_token_id': self.order_id.payment_token_id.id,
                        })
                        if request and request.session:
                            tx_ids_list = set(request.session.get("__payment_tx_ids__", [])) | set(tx.ids)
                            request.session["__payment_tx_ids__"] = list(tx_ids_list)
                        # PaymentProcessing.add_payment_transaction(tx)
                        tx._cron_post_process_after_done()
                        template_id = self.env.ref('sale_order_subscription_payment_stripe.invoice_payment_email_template')
                        if template_id:
                            template_id.send_mail(invoice.id, force_send=True)
                        _logger.info('<%s> transaction <%s> completed, reconciled invoice %s (ID %s))',
                            acquirer_id.provider, tx.id, invoice.name, invoice.id)
                    elif latest_invoice.get('id') and latest_invoice.get('status') != 'paid':
                        invoice.write({
                            'stripe_invoice_ref': latest_invoice['id'],
                        })
                        tx.write({
                            'state': 'cancel',
                            'state_message': latest_invoice.get('status'),
                            'payment_token_id': self.order_id.payment_token_id.id,
                        })
                        _logger.info('<%s> transaction <%s> failed, reconciled invoice %s (ID %s))',
                            acquirer_id.provider, tx.id, invoice.name, invoice.id)         
                else:
                    raise ValidationError(_("Stripe Subscription Failed %s" % (stripe_subscription.get('status'))))
        return invoice
