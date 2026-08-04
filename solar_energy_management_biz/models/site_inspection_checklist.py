# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models, fields
import logging

logger = logging.getLogger(__name__)

class SiteInspectionChecklist(models.Model):
    _name = 'site.inspection.checklist'
    _description = "Site Inspection Checklist"

    inspection_id = fields.Many2one('site.inspection')
    checklist_line_id = fields.Many2one('checklist.line')

    checklist_name = fields.Char()
    is_approve = fields.Boolean()