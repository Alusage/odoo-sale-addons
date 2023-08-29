# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Sale Order Subscription',
    'version': '1.0.0',
    'summary': """
        This module adds a subscription mechanism to sale orders and allows to automatically generate recurring invoices based on the subscription period.
        This allow to manage automatic payments for recurring services. (with additional module: sale_subscription_payment_stripe, sale_subscription_payment_gocardless)
    """,
    'description': """
    """,
    'author': 'Nicolas JEUDY',
    'website': 'https://github.com/Alusage/odoo-sale-addons',
    'license': 'AGPL-3',
    'category': 'Sales',
    'depends': [
        'sale',
        'account',
        'sales_team',
        'onchange_helper',
        'payment'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/subscription_data.xml',
        'views/sale_order_view.xml',
        'views/product_template_view.xml',
    ],
    'demo': [],
    'auto_install': False,
    'external_dependencies': [],
    'application': True,
    'css': [],
    'images': [],
    'installable': True,
    'maintainer': 'Nicolas JEUDY',
    'pre_init_hook': '',
    'post_init_hook': '',
    'uninstall_hook': '',
}
