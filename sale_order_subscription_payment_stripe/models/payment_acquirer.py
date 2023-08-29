# -*- coding: utf-8 -*-

import logging

from odoo import api, models, _

_logger = logging.getLogger(__name__)

try:
    import stripe
except ImportError:
    _logger.error('Odoo module payment_stripe_recurring_acs depends on the stripe python module')
    stripe = None


class PaymentTransactionStripe(models.Model):
    _inherit = "payment.transaction"

    def _stripe_create_payment_intent(self, acquirer_ref=None, email=None):
        """ Overide this method for update context for off session stripe sca payment. """
        context = dict(self.env.context or {})
        if not context.get('website_id'):
            context.update({'off_session': True})
            self.env.context = context
        return super(PaymentTransactionStripe, self)._stripe_create_payment_intent(acquirer_ref=acquirer_ref, email=email)

    def _stripe_s2s_validate_tree(self, tree):
        """ Overide method for confirm payment after 'done' transactions. """
        res = super(PaymentTransactionStripe, self)._stripe_s2s_validate_tree(tree=tree)
        if self.payment_id and self.state == 'done':
            self._cron_post_process_after_done()
        return res


class PaymentTokenStripe(models.Model):
    _inherit = 'payment.token'

    @api.model
    def stripe_create(self, values):
        """ Overide this method for modify customer for set default payment method. """
        res = super(PaymentTokenStripe, self).stripe_create(values=values)
        if values.get("stripe_payment_method") and values.get('acquirer_id') and res.get('acquirer_ref'):
            payment_acquirer = self.env["payment.acquirer"].browse(values['acquirer_id'])
            stripe.api_key = payment_acquirer.stripe_secret_key
            stripe.Customer.modify(
                res['acquirer_ref'],
                invoice_settings={'default_payment_method': values['stripe_payment_method']}
            )
        return res
