# -*- coding: utf-8 -*-
import odoo
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_display_dpa_text = fields.Boolean(
        string="Display down payment amount in letters on report", default=False, default_model='sale.order'
    )
