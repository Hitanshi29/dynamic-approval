# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models,fields, api

class TeamManagement(models.Model):
    _name = 'team.management'
    _description = 'Team Management'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True ,copy=False, readonly=True, index='trigram', default=lambda self: ('New'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('team_type') == 'survey_team':
                vals['name'] = self.env['ir.sequence'].next_by_code('survey.team')

            elif vals.get('team_type') == 'site_inspection_team':
                vals['name'] = self.env['ir.sequence'].next_by_code('installation.team')

            elif vals.get('team_type') == 'qa_team':
                vals['name'] = self.env['ir.sequence'].next_by_code('qa.team')

        return super().create(vals_list)

    team_type = fields.Selection([
        ('survey_team','Survey Team'),
        ('site_inspection_team','Installation Team'),
        ('qa_team','Quality  Assurance Team'),
    ],string="Team Template")

    state = fields.Selection([
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('working', 'Working'),
        ('completed', 'Completed')
    ], string='Status',default='available',tracking=True,readonly=True,group_expand='_group_expand_states')

    @api.model
    def _group_expand_states(self, states, domain):
        return [
            'available',
            'assigned',
            'working',
            'completed',
        ]

    leader_id = fields.Many2one('res.partner',string='Project manager',)

    member_ids = fields.Many2many('res.partner',string='Members',)

    company_id = fields.Many2one('res.company',default=lambda self: self.env.company)

    inspection_count = fields.Integer(string="Completed Inspections",compute="_compute_inspection_count")

    def _compute_inspection_count(self):
        inspection_obj = self.env['site.inspection']

        for rec in self:
            rec.inspection_count = inspection_obj.search_count([
                ('team_id', '=', rec.id),
                # ('state', '=', 'approve')
            ])

    def action_view_inspections(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Site Inspections',
            'res_model': 'site.inspection',
            'view_mode': 'list,form',
            'domain': [
                ('team_id', '=', self.id),
            ],
        }
    
    installation_count = fields.Integer(string="Completed Installation",compute="_compute_installation_count")

    def action_view_installation(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Project Installation Task',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [
                ('installation_team_id', '=', self.id),
            ],
        }

    def _compute_installation_count(self):
        installation_obj = self.env['project.task']

        for rec in self:
            rec.installation_count = installation_obj.search_count([
                ('installation_team_id', '=', rec.id),
                # ('stage_id', '=', 'approve')
            ])

    qa_count = fields.Integer(string="Completed QA",compute="_compute_qa_count")


    def action_view_qa(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Project QA Task',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [
                ('qa_team_id', '=', self.id),
            ],
        }

    def _compute_qa_count(self):
        qa_obj = self.env['project.task']

        for rec in self:
            rec.qa_count = qa_obj.search_count([
                ('qa_team_id', '=', rec.id),
            ])


    current_inspection_id = fields.Many2one(
        'site.inspection',
        string="Site Inspection Id",
        compute='_compute_current_inspection'
    )

    start_date = fields.Datetime(
        string="Work Start Date",
        readonly=True
    )

    completion_date = fields.Datetime(
        string="Work Completion Date",
        readonly=True
    )

    def _compute_current_inspection(self):
        for rec in self:

            inspection = self.env['site.inspection'].search([
                ('team_id', '=', rec.id),
                ('approve_status', 'not in', ['approve', 'reject']),
                ('state', 'not in', ['cancel'])
            ], limit=1)

            rec.current_inspection_id = inspection


    current_installation_id = fields.Many2one(
        'ren.order',
        string="Installation Order Id",
        compute="_compute_current_installation"
    )

    current_installation_task_id = fields.Many2one(
        'project.task',string="Installation Task Id")

    def _compute_current_installation(self):
        for rec in self:
            task = self.env['ren.order'].search([
                ('installation_team_id', '=', rec.id),
                ('state', 'not in', ['qa', 'complete', 'cancel'])
            ], limit=1)

            rec.current_installation_id = task

            

    current_qa_id = fields.Many2one(
        'ren.order',
        string="QA Order Id",
        compute="_compute_current_qa"
    )

    current_qa_task_id = fields.Many2one(
        'project.task',string="QA Task Id")

    def _compute_current_qa(self):
        for rec in self:
            task = self.env['ren.order'].search([
                ('qa_team_id', '=', rec.id),
                ('state', 'not in', ['complete', 'cancel'])
            ], limit=1)

            rec.current_qa_id = task