from odoo import api, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
            Override method for remove Make Recurring AccountMove
        """
        res = super(AccountMove, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        context = dict(self._context) or {}
        if context.get('default_move_type') != 'out_invoice' and res and res.get('toolbar'):
            for action in res.get('toolbar').get('action'):
                if action.get('name') == 'Make Recurring':
                    res.get('toolbar').get('action').remove(action)
        if view_type == 'tree' and res and res.get('toolbar'):
            for action in res.get('toolbar').get('action'):
                if action.get('name') == 'Make Recurring':
                    res.get('toolbar').get('action').remove(action)
        return res
