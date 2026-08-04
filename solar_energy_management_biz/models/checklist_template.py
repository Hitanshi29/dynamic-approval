# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models, fields, api
import logging

logger = logging.getLogger(__name__)

class QaChecklist(models.Model):
    _name = 'checklist.template'
    _description = 'Checklist Template'

    name = fields.Char(string="Template Name",required=True)
    line_ids = fields.One2many('checklist.line','template_id',string="Checklist Items")

    checklist_type = fields.Selection([
        ('survey_template','Survey Template'),
        ('qa_template','Quality  Assurance Template'),
    ],string="Checklist Template")