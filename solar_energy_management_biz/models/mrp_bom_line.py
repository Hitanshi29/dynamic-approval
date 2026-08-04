# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import api, fields, models

class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    available_qty = fields.Float(string="Available Qty",compute="_compute_stock_status")

    availability = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available')
    ], string="Status", compute="_compute_stock_status")

    @api.depends('product_id', 'product_qty')
    def _compute_stock_status(self):
        for line in self:
            available = line.product_id.free_qty    

            line.available_qty = available

            if available >= line.product_qty:
                line.availability = 'available'
            else:
                line.availability = 'not_available'