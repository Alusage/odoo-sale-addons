# -*- coding: utf-8 -*-
import odoo
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    down_payment_amount = fields.Monetary(
        string="Down payment amount", compute="get_down_payment_amount"
    )
    display_dpa_text = fields.Boolean(
        string="Display down payment amount in letters on report", default=False
    )
    down_payment_amount_text = fields.Char(
        string="Down payment amount in letters", compute="get_dpa_text"
    )

    @api.depends("amount_total", "payment_term_id")
    def get_down_payment_amount(self):
        """
        Calculates the down payment amount based on :
        - the sale order total amount,
        - the payment term if its first line is a fixed amount or a percentage.
        Returns 0.0 otherwise.
        """
        for order in self:
            amount = 0.0
            payment_term_id = order.payment_term_id
            if payment_term_id and payment_term_id.line_ids:
                line0 = payment_term_id.line_ids[0]
                if line0.value == "percent":
                    amount = order.amount_total * line0.value_amount / 100.0
                elif line0.value == "fixed":
                    amount = line0.value_amount
            order.down_payment_amount = amount

    @api.depends("down_payment_amount")
    def get_dpa_text(self):
        """
        Converts the down payment amount to text, using the sale order currency built-in method.
        """
        for order in self:
            odpa = order.down_payment_amount
            cur_id = order.currency_id
            dpa_text = ""
            if odpa and cur_id:
                dpa_text = cur_id.amount_to_text(odpa)
            order.down_payment_amount_text = dpa_text

