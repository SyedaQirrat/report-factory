# -*- coding: utf-8 -*-
{
    'name': 'Mulphico Inventory Valuation Report',
    'version': '18.0.1.0.0',  # <-- This is the updated line
    'summary': 'Custom inventory valuation report on Odoo screen.',
    'description': """
        This module generates a custom FIFO inventory valuation report 
        as an Odoo QWeb (HTML) report.
    """,
    'category': 'Inventory/Reporting',
    'author': 'Syeda Qirrat',
    'depends': [
        'stock',
        'product',
        'mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/report_action.xml',           
        'report/report_template.xml',
        'views/report_menus.xml',
        'views/inventory_report_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}