# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models, fields, api
import logging

logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order.line'

    is_bom_component = fields.Boolean(default=False)

    # is_hidden = fields.Boolean(default=False)