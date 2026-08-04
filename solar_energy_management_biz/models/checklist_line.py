# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models, fields, api
import logging

logger = logging.getLogger(__name__)

class QaChecklistLine(models.Model):
    _name = 'checklist.line'
    _description = 'Checklist Line'

    template_id = fields.Many2one('checklist.template',string="Template Data")

    name = fields.Char(string="Checklist Item")