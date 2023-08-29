# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    stripe_invoice_ref = fields.Char("Stripe Invoice Reference", copy=False)