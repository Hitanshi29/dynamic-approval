# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models, fields, api
import logging

logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_solar_project = fields.Boolean(string="Solar Project")


    def action_confirm(self):
        res = super().action_confirm()

        for order in self:
            if not order.is_solar_project:
                continue

            project = self.env['project.project'].search([
                ('sale_line_id.order_id', '=', order.id)
            ], limit=1)

            if project:
                project.sale_order_id = order.id

  
        return res
        
    def action_view_inspection(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Site Inspection',
            'res_model': 'site.inspection',
            'view_mode': 'form,list',
            'context': {
                'default_quotation_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_lead_id': self.opportunity_id.id
            },
        }

    has_bom_product = fields.Boolean(
        compute="_compute_has_bom_product",
        store=True
    )

    @api.depends('order_line.product_id')

    def _compute_has_bom_product(self):
        for order in self:
            order.has_bom_product = False

            for line in order.order_line:
                bom = self.env['mrp.bom'].search([
                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)
                ], limit=1)

                if bom:
                    order.has_bom_product = True
                    break

    def action_expand_bom(self):
        for order in self:
            for line in order.order_line.filtered(lambda l: not l.is_bom_component):

                bom = self.env['mrp.bom'].search([
                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)
                ], limit=1)

                if not bom:
                    continue

                seq = line.sequence + 0.01

                for bom_line in bom.bom_line_ids:

                    existing_line = order.order_line.filtered(
                        lambda l:
                            l.is_bom_component and
                            l.product_id == bom_line.product_id
                    )

                    if existing_line:
                        continue

                    self.env['sale.order.line'].create({
                        'order_id': order.id,
                        'product_id': bom_line.product_id.id,
                        'product_uom_qty': bom_line.product_qty * line.product_uom_qty,
                        'price_unit': 0,
                        'sequence': seq,
                        'name': bom_line.product_id.display_name,
                        'is_bom_component': True,
                    })

                    seq += 0.01

    
    def action_hide_bom(self):
        self.order_line.filtered(
            lambda l: l.is_bom_component
        ).unlink()

      
    def action_refresh_bom(self):
        self.action_hide_bom()
        self.action_expand_bom()