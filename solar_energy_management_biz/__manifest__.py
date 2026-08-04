# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

{
    'name': 'Solar Energy Management Biz',
    'version': '1.0',
    'author': 'Bizople Solutions Pvt. Ltd.',
    'website': 'https://www.bizople.com',
    'summary': '',
    'description': "",
        
    'depends': ['crm','sale_management','mrp', 'project','sale_project','purchase'],
    'data': [
        'security/solar_energy_security.xml',
        'security/ir.model.access.csv',

        'report/ir_actions_report.xml',
        'report/site_inspection_report.xml',


        'data/solar_project_demo.xml',
        'data/ir_sequence.xml',
        'data/mail_template_data.xml',
        
        
        'views/crm_lead_view.xml',
        'views/sale_order_view.xml',
        'views/site_inspection_view.xml',
        'views/ren_order_view.xml',
        'views/project_task_view.xml',
        'views/team_management_view.xml',
        'views/checklist_template_view.xml',
        'views/menu.xml',
    ],
    'sequence': 1,
    'application': True,
    'installable': True,
    'license': 'Other proprietary',
}