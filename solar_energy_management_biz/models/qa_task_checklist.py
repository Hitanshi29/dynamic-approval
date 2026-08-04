# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models, fields
import logging

logger = logging.getLogger(__name__)

class QaTaskChecklist(models.Model):
    _name = 'qa.task.checklist'
    _description = 'QA Task Checklist'

    project_task_id = fields.Many2one('project.task')
    checklist_line_id = fields.Many2one('checklist.line')
    checklist_name = fields.Char()
    is_approve = fields.Boolean()