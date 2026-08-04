# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models , fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # customer_type = fields.Selection([
    #     ('residential','Residential'),
    #     ('commercial','Commercial'),
    #     ('industrial','Industrial')
    # ],string='Customer Type')

    required_capacity = fields.Float(string='Required Capacity')

    monthly_electricity_bill = fields.Float(string='Monthly Electricity Bill')

    unit_cpnsumption = fields.Float(string='Unit Consumption')

    roof_type = fields.Selection([
        ('rcc', 'RCC Roof'),
        ('metal', 'Metal Sheet'),
        ('tile', 'Tile Roof'),
        ('other', 'Other')
    ], string='Roof Type')

    roof_area = fields.Float(string='Roof Area Available(Sq. Ft.)')

    installation_location = fields.Text(string='Installation Location')

    battery_required = fields.Boolean(string='Battery Required')

    installation_date = fields.Date(string='Preffered Installation Date')

    grid_type = fields.Selection([
        ('ongrid','On-Grid'),
        ('offgrid','Off-Grid'),
        ('hybrid','Hybrid')
    ],string='Grid Type')

    def action_view_inspection(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Site Inspection',
            'res_model': 'site.inspection',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
        }

    def action_create_inspection(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Site Inspection',
            'res_model': 'site.inspection',
            'view_mode': 'form,list',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_lead_id': self.id
            },
        }

    
    inspection_count = fields.Integer(compute='_compute_counts')
    def _compute_counts(self):
        for rec in self:
            rec.inspection_count = self.env['site.inspection'].search_count([('lead_id', '=', rec.id)])
