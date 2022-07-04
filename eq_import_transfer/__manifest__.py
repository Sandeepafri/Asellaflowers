# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

{
    'name': "Import Transfer",
    'category': 'Inventory',
    'version': '15.0.1.0',
    'author': 'Equick ERP',
    'summary': """ import transfer from xls file.""",
    'depends': ['base','stock_account','sh_inventory_analytics','stock_force_date_app'],
    'license': 'OPL-1',
    'website': "",
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'wizard/wizard_transfer_view.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: