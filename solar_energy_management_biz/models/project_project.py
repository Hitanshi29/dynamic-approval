# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models , fields
import logging

logger = logging.getLogger(__name__)

class projectProject(models.Model):
    _inherit = 'project.project'

    sale_order_id = fields.Many2one('sale.order',string='Sale Order')

    ren_order_id = fields.Many2one('ren.order',string='Renewable Order')