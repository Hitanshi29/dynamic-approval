# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models , fields, api
import logging

logger = logging.getLogger(__name__)

class projectTask(models.Model):
    _inherit = 'project.task'

    inspection_id = fields.Many2one('site.inspection',string="Site Inspections",readonly=True)

    site_address = fields.Text(related="inspection_id.site_address",string="site Address")
    site_type = fields.Selection(related="inspection_id.site_type",string="Site Type")
    roof_type = fields.Selection(related="inspection_id.roof_type",string="Roof Type")
    # roof_area = fields.Float(related="inspection_id.roof_area",string="Roof Area")
    required_capacity = fields.Float(related="inspection_id.required_capacity",string="Required Capacity")
    recommended_capacity = fields.Float(related="inspection_id.recommended_capacity",string="Recommended Capacity")
    meter_type = fields.Selection(related="inspection_id.meter_type",string="Meter Type")
    average_bill = fields.Float(related="inspection_id.average_bill",string="Avarage Bill")
    shading_present = fields.Boolean(related="inspection_id.shading_present",string="shading Present")
    # shading_details = fields.Text(related="inspection_id.shading_details",string="Shading Details")
    feasibility = fields.Selection(related="inspection_id.feasibility",string="Faasibility")

    task_type = fields.Selection([
        ('installation', 'Installation'),
        ('qa', 'QA'),
    ])

    is_subcontract = fields.Boolean(string="Is Sub Contractor")

    # check_type = fields.Selection([
    #     ('internal', 'Internal Team'),
    #     ('subcontract', 'Sub Contractor')
    # ], default='internal', string="Installation Type")

    ren_order_id = fields.Many2one('ren.order',string="REN Order")

    installation_team_id = fields.Many2one('team.management', string="Team")
    installation_leader_id = fields.Many2one(related="installation_team_id.leader_id", string="Team Leader")
    intsallation_team_type = fields.Selection(related="installation_team_id.team_type",string="Team type")
    installation_subcontractor_id = fields.Many2one('res.partner',string="Sub Contractor")



    qa_team_id = fields.Many2one('team.management', string="QA Team")
    qa_leader_id = fields.Many2one(related="qa_team_id.leader_id", string="QA Team Leader")
    qa_team_type = fields.Selection(related="qa_team_id.team_type",string="QA Team type")
    qa_subcontractor_id = fields.Many2one('res.partner',string="Sub Contractor Of QA")


    checklist_template_ids = fields.Many2many('checklist.template',string="Template Name",domain=[('checklist_type', '=', 'qa_template')])

    all_checklist_line_ids = fields.One2many(
        'qa.task.checklist','project_task_id'
    )

    @api.onchange('checklist_template_ids')
    def _onchange_checklist_templates(self):

        selected_names = []

        for template in self.checklist_template_ids:
            for line in template.line_ids:
                if line.name not in selected_names:
                    selected_names.append(line.name)

        self.all_checklist_line_ids = self.all_checklist_line_ids.filtered(
            lambda l: l.checklist_name in selected_names
        )


        existing_names = self.all_checklist_line_ids.mapped('checklist_name')

        for name in selected_names:
            if name not in existing_names:
                self.all_checklist_line_ids += self.all_checklist_line_ids.new({
                    'checklist_name': name,
                })