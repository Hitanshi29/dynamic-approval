# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.
{
    'name': 'Dynamic Approval',
    'description': "",
    'summary': "",
    'version': '19.0.0.0',
    'author': 'Bizople Solutions Pvt. Ltd.',
    'website': 'https://www.bizople.com/',
    'depends': [
        'mail',
    ],
    'data': [
        'security/dynamic_approval_access.xml',
        'security/ir.model.access.csv',
        'data/ir.sequence.xml',
        'views/multi_approval_type_view.xml',
        'views/approval_request_view.xml',
        'wizard/approval_change_user_view.xml',
        'views/menu.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'dynamic_approval/static/src/components/**/*',
    #     ],
    # },
    'sequence' : 1,
    'installable': True,
    'application': True,
    'license': 'Other proprietary',
}
