# -*- coding: utf-8 -*-

{
    'name': 'Sale Order Subscription Stripe Payment',
    'version': '1.0',
    'author': 'Nicolas JEUDY',
    'website': 'https://github.com/Alusage/odoo-sale-addons',
    'sequence': 15,
    'summary': 'Payment Acquirer: Stripe subscription Implementation',
    'description': """Stripe subscription Payment Acquirer: Allow customer to pay amount via subscription.
    """,
    'depends': [
        'payment_stripe',
        'sale_order_subscription',
        'account_payment',
        'website_payment'
    ],
    'data': [
        'data/mail_template.xml',
        'security/security.xml',
        'views/sale_order_view.xml',
        'views/payment_acquirer_view.xml',
        'views/assets.xml'
    ],
    'demo': [],
    'external_dependencies': {
        "python": [
            "stripe",
        ],
    },
    'images': [
    ],
    'price': 70.0,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'category': 'Sales',
}
