# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Sale Order Down Payment',
    'version': '1.0.0',
    'summary': """
        This module displays down payment amount on sale orders according to the payment term first line if it's a percent or fixed one.
        In addition, you can chose to display fully spelled out the down payment amount on PDF report.
    """,
    'description': """
    """,
    'author': 'RemiFr82',
    'website': 'https://remifr82.me',
    'license': 'AGPL-3',
    'category': 'Sales',
    'depends': [
        'sale',
    ],
    'data': [
        'reports/sale_order_reports.xml',
        'views/sale_order.xml',
    ],
    'demo': [],
    'auto_install': False,
    'external_dependencies': [],
    'application': False,
    'css': [],
    'images': [],
    'installable': True,
    'maintainer': 'RemiFr82',
    'pre_init_hook': '',
    'post_init_hook': '',
    'uninstall_hook': '',
}
