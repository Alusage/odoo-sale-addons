# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'payment.acquirer'

    subscription_ok = fields.Boolean("Subscription")