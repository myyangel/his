# -*- coding: utf-8 -*-

{
    'name': 'Agenda',
    'version': '1.0.0',
    'author': 'MSTECH',
    'category': 'Technical Configuration',
    'license': 'AGPL-3',
    'website': 'https://www.mstech.pe',
    'depends': [
        'product',
        'hr',
        'mail',
        'web_gantt',
    ],
    'data': [
        'data/ir_cron_data.xml',
        'security/planner_security.xml',
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/planner_views.xml',
    ],
    'installable': True,
    'sequence': 1,
}
