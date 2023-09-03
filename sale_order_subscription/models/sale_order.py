# -*- coding: utf-8 -*-

import logging

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _, _lt
from odoo.exceptions import UserError, ValidationError
from odoo.tools import get_timedelta

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange("subscription_type")
    def _onchange_subscription_type(self):
        if self.subscription_type:
            self.subscription_state = 'draft'
            self.require_payment = True
        else:
            self.subscription_state = False

    @api.onchange("date_order","subscription_type")
    def get_date_init(self):
        default_date = False  
        if self.date_order and self.subscription_type:
            self.date_init = self.date_order + relativedelta(months=self.subscription_type.interval)


    subscription_type = fields.Many2one('sale.subscription.type')
    exec_init = fields.Integer(string='Recurring Number', required=False, default=1)
    date_init = fields.Datetime(string='Start Date', required=False)
    subscription_state = fields.Selection([('draft', 'Draft'), ('running', 'Running'), ('done', 'Done'), ('cancel', 'Cancel')], string='Status', copy=False, default='draft')
    subscription_schedule_ids = fields.One2many('sale.subscription.schedule', 'order_id', copy=False)
    has_subscription = fields.Boolean("Has Subscription", store=True, compute='_has_subscription')
    is_subscription_order = fields.Boolean("IS Subscription", store=True, compute='_has_subscription')
    subscription_payment_acquirer_id = fields.Many2one('payment.acquirer', string='Automatic payment', help='You need a payment acquierer if you want automated payment', tracking=True, copy=False)
    subscription_note = fields.Char('Subscription infos')

    @api.depends('order_line', 'subscription_type')
    def _has_subscription(self):
        for record in self:
            record.has_subscription = False
            record.is_subscription_order = False
            if record.subscription_type and record.order_line.filtered(lambda r: r.product_id.subscription_ok):
                record.is_subscription_order = True
            if record.order_line.filtered(lambda r: r.product_id.subscription_ok):
                record.has_subscription = True

    def _get_last_subscription_invoice(self):
        self.ensure_one()
        return self.invoice_ids.sorted(key=lambda r: r.invoice_date, reverse=True)[0]

    def action_subscription_schedule(self):
        for rec in self:
            schedules= []
            recent_date = rec.date_init
            if not rec.subscription_schedule_ids:
                if rec.invoice_ids:
                    for count in range(rec.exec_init):
                        vals ={
                            'date': recent_date,
                            'status': 'not_created',
                            'template_invoice_id': rec._get_last_subscription_invoice().id,
                            'order_id': rec.id,
                        }
                        schedules += rec.subscription_schedule_ids.create(vals)
                        if rec.subscription_type and rec.subscription_type.unit == 'day':
                            recent_date = recent_date + relativedelta(days=rec.subscription_type.interval)
                        elif rec.subscription_type and rec.subscription_type.unit == 'week':
                            recent_date = recent_date  + relativedelta(weeks=rec.subscription_type.interval)
                        elif rec.subscription_type and rec.subscription_type.unit == 'month':
                            recent_date = recent_date  + relativedelta(months=rec.subscription_type.interval)
                        elif rec.subscription_type and rec.subscription_type.unit == 'year':
                            recent_date = recent_date  + relativedelta(months=rec.subscription_type.interval)
                else:
                    raise UserError(_('You should create at least on invoice for this order before !'))
            rec.write({
                'subscription_state': 'running',
            })

    def action_subscription_cancel(self):
       self.write({'subscription_state': 'cancel'})
       for rec in self:
            rec.subscription_schedule_ids.filtered(lambda s: s.status == 'not_created').unlink()  

    def unlink(self):
        if any(self.filtered(lambda s: s.subscription_state == "running")):
            raise UserError(_('You cannot delete an active subscription!'))
        return super(SaleOrder, self).unlink()

class SaleRecurrenceType(models.Model):
    _name = "sale.subscription.type"
    _description = "Subscription Type"
    _order = "unit,interval"

    active = fields.Boolean(default=True)
    name = fields.Char(compute='_compute_name', store=True, readonly=False)
    interval = fields.Integer(string="Duration", required=True, default=1,
        help="Recurence Interval")
    unit = fields.Selection([('day', 'Days'), ("week", "Weeks"), ("month", "Months"), ('year', 'Years')],
        string="Unit", required=True, default='month')

    _sql_constraints = [
        ('subscription_interval', "CHECK(interval >= 0)", "The subscription interval has to be greater or equal to 0."),
    ]

    @api.depends('interval', 'unit')
    def _compute_name(self):
        for record in self:
            if not record.name:
                record.name = _("%s %s", record.interval, record.unit)

    def get_recurrence_timedelta(self):
        self.ensure_one()
        return get_timedelta(self.duration, self.unit)

class Schedule(models.Model):
    _name = "sale.subscription.schedule"
    _description = "Subscription Schedule"
    _rec_name = 'status'

    date = fields.Datetime('Schedule Date')
    status = fields.Selection([('not_created', 'Not Created'),('created', 'Created')], string='Status', default='not_created')
    # Add Invoice Recurring
    invoice_id = fields.Many2one('account.move', string="Generated invoice")
    payment_state = fields.Selection(related="invoice_id.payment_state", readonly=True)
    template_invoice_id = fields.Many2one('account.move', string="Invoice")
    order_id = fields.Many2one('sale.order', string="Subscription")

    @api.model
    def _process_subscription_schedule(self):
        schedules = self.search([('order_id.state', '=', 'sale'), ('status', '=', 'not_created'), '|', ('date', '<', fields.Datetime.now()), ('date', '=', False)])
        for subscription in schedules:
            new_invoice = subscription.template_invoice_id.copy()
            vals = {
                'invoice_line_ids': new_invoice.invoice_line_ids.filtered(lambda o: o.product_id.subscription_ok).ids,
            }
            new_invoice.write(vals)
            _logger.info('Subscription: %s' % subscription.order_id.name)
            new_invoice = subscription.process_payment(new_invoice)
            subscription.write({
                'invoice_id': new_invoice.id,
                'status': 'created',
            })   
    
    @api.model
    def process_payment(self, invoice):
        return invoice