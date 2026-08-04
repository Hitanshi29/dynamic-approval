# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models,fields, api
from odoo.fields import Command
from odoo.exceptions import ValidationError

import logging
logger = logging.getLogger(__name__)

class RenOrder(models.Model):
    _name = 'ren.order'
    _description = 'REN Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True ,copy=False, readonly=True, index='trigram', default=lambda self: ('New'))

    customer_id = fields.Many2one('res.partner', string="Customer",required=True,readonly=True)
    email_from = fields.Char(related="customer_id.email",string="Email")
    phone_from = fields.Char(related="customer_id.phone",string="Phone")

    lead_id = fields.Many2one('crm.lead', required=True,string="Lead",readonly=True)

    quotation_id = fields.Many2one('sale.order', string="Quotation",required=True,readonly=True)

    company_id = fields.Many2one('res.company',default=lambda self: self.env.company)

    quotation_amount = fields.Float(string="Quotation Amount")

    currency_id = fields.Many2one('res.currency',related='company_id.currency_id',readonly=True)

    site_inspection_id = fields.Many2one('site.inspection',string="Site Inspection",required=True,readonly=True)

    site_address = fields.Text(related="site_inspection_id.site_address",string="site Address")
    site_type = fields.Selection(related="site_inspection_id.site_type",string="Site Type")
    roof_type = fields.Selection(related="site_inspection_id.roof_type",string="Roof Type")
    # roof_area = fields.Float(related="site_inspection_id.roof_area",string="Roof Area")
    required_capacity = fields.Float(related="site_inspection_id.required_capacity",string="Required Capacity")
    recommended_capacity = fields.Float(related="site_inspection_id.recommended_capacity",string="Recommended Capacity")
    meter_type = fields.Selection(related="site_inspection_id.meter_type",string="Meter Type")
    average_bill = fields.Float(related="site_inspection_id.average_bill",string="Avarage Bill")
    shading_present = fields.Boolean(related="site_inspection_id.shading_present",string="shading Present")
    # shading_details = fields.Text(related="site_inspection_id.shading_details",string="Shading Details")
    feasibility = fields.Selection(related="site_inspection_id.feasibility",string="Faasibility")


    bom_ids = fields.Many2many('mrp.bom',string="Bill Of Material",)
    bom_product_ids = fields.Many2many('mrp.bom.line',compute="_compute_bom_line_ids")

    @api.depends('bom_ids')
    def _compute_bom_line_ids(self):
        for rec in self:
            rec.bom_product_ids = rec.bom_ids.mapped('bom_line_ids')

    order_date = fields.Date(string="Order Date")

    state = fields.Selection([
        ('new', 'New'),
        ('material_order', 'Material Order'),
        ('material_arrived', 'Material Arrived'),
        ('installation', 'Installation'),
        ('qa', 'QA'),
        ('complete', 'Completed'),
        ('cancel','Cancel')
    ], default='new',tracking=True,group_expand='_group_expand_states')


    @api.model
    def _group_expand_states(self, states, domain):
        return [
            'new',
            'material_order',
            'material_arrived',
            'installation',
            'qa',
            'complete',
            'cancel',
        ]

    def material_request(self):
        self.write({'state': 'material_order'})
    
    # def material_arrived(self):
    #     self.write({'state': 'material_arrived'})

    def material_arrived(self):
        for order in self:
            missing_products = []

            for bom_line in order.bom_product_ids:
                available_qty = bom_line.product_id.free_qty   

                if available_qty < bom_line.product_qty:
                    missing_products.append(bom_line.product_id.display_name
                        # "%s (Required: %s, Available: %s)" % (
                        #     bom_line.product_id.display_name,
                        #     bom_line.product_qty,
                        #     available_qty
                        # )
                    )

            if missing_products:
                raise ValidationError(
                    "The following BOM components are not available in sufficient quantity:\n\n%s\n\n"
                    "Please purchase and receive these products before changing the state to Material Arrived."
                    % ("\n".join(missing_products))
                )

            order.state = 'material_arrived'

    def action_installation(self):
        self.write({'state': 'installation'})


    
    def action_qa(self):
        # self.write({'state': 'qa'})

        for rec in self:
            rec.state = 'qa'

            if rec.installation_team_id:
                self.installation_team_id.write({
                    'state': 'available',
                    'current_installation_task_id': False,
                    # 'current_installation_id': False
                })
    
    def action_complete(self):
        # self.write({'state': 'complete'})

        for rec in self:
            rec.state = 'complete'
            # self.write({'state': 'installation'})

            if rec.qa_team_id:
                self.qa_team_id.write({
                    'state': 'available',
                    'current_qa_task_id': False,
                    'current_qa_id': False
                })
    
    def action_cancel(self):
        self.write({'state': 'cancel'})

    is_purchase_order = fields.Boolean(string="Purchase Order")

    vendor_id = fields.Many2one(
        'res.partner',
        string="Vendor",
    )

    installation_type = fields.Selection([
        ('internal_team', 'Internal Team'),
        ('sub_contract', 'Sub Contract'),
    ], string="Installation Type")

    installation_team_id = fields.Many2one('team.management', string="Team",domain=[('state', '=', 'available'),('team_type','=','installation_team')])
    installation_leader_id = fields.Many2one(related="installation_team_id.leader_id", string="Team Leader")
    installation_leader_email = fields.Char(related="installation_team_id.leader_id.email",string="Leader Email")
    installation_start_date = fields.Date(string="Start Date")
    installation_end_date = fields.Date(string="End Date")
    installation_subcontractor_id = fields.Many2one('res.partner',string="Sub Contractor")
    installation_allocate_time = fields.Float(string="Installation Allocation Time")

    project_id = fields.Many2one(
        'project.project',
        string='Project'
    )

    installation_task_id = fields.Many2one(
        'project.task',
        string='Installation Task'
    )

    qa_task_id = fields.Many2one(
        'project.task',
        string='QA Task'
    )

    def _get_or_create_project(self):
        self.ensure_one()

        if self.project_id:
            return self.project_id

        project = self.env['project.project'].create({
            'name': self.name,
            'partner_id': self.customer_id.id,
            'allow_billable': True,
            'type_ids': [
                Command.link(self.env.ref('project.project_stage_0').id),
                Command.link(self.env.ref('project.project_stage_1').id),
                Command.link(self.env.ref('project.project_stage_2').id),
                Command.link(self.env.ref('project.project_stage_3').id),
            ],
        })


        self.project_id = project.id
        return project

    def action_create_installation_task(self):
        self.ensure_one()

        project = self._get_or_create_project()

        task = self.env['project.task'].create({
            'name': f'Installation - {self.name}',
            'project_id': project.id,
            'installation_team_id': self.installation_team_id.id,
            'task_type': 'installation',
            'is_subcontract': False,
            'inspection_id': self.site_inspection_id.id,
            'allocated_hours': self.installation_allocate_time,
            'date_deadline': self.installation_end_date
        })

        self.installation_task_id = task.id

        if self.installation_team_id:
            self.installation_team_id.write({
                'state': 'working',
                'current_installation_task_id': self.installation_task_id
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Installation Task',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': task.id,
            'target': 'current',
        }

    def action_subcontract_installation_task(self):
        self.ensure_one()

        project = self._get_or_create_project()

        task = self.env['project.task'].create({
            'name': f'Installation - {self.name}',
            'project_id': project.id,
            'partner_id': self.installation_subcontractor_id.id,
            'installation_subcontractor_id': self.installation_subcontractor_id.id,
            'task_type': 'installation',
            'is_subcontract': True,
            'inspection_id': self.site_inspection_id.id,
            'allocated_hours': self.installation_allocate_time,
            'date_deadline': self.installation_end_date
        })

        self.installation_task_id = task.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Installation Task',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': task.id,
            'target': 'current',
        }

    qa_type = fields.Selection([
        ('internal_team', 'Internal Team'),
        ('sub_contract', 'Sub Contract'),
    ], string="QA Inspection Type")

    qa_team_id = fields.Many2one('team.management', string="QA Team",domain=[('state', '=', 'available'),('team_type','=','qa_team')])
    qa_leader_id = fields.Many2one(related="qa_team_id.leader_id", string="QA Team Leader")
    qa_leader_email = fields.Char(related="qa_team_id.leader_id.email",string="QA Leader Email")
    qa_start_date = fields.Date(string="Start Date Of QA")
    qa_end_date = fields.Date(string="End Date Of QA")
    qa_subcontractor_id = fields.Many2one('res.partner',string="QA Sub Contractor")
    qa_allocate_time = fields.Float(string="QA Allocation Time")


    def action_create_qa_task(self):
        self.ensure_one()

        project = self._get_or_create_project()

        task = self.env['project.task'].create({
            'name': f'QA - {self.name}',
            'project_id': project.id,
            'qa_team_id': self.qa_team_id.id,
            'task_type': 'qa',
            'is_subcontract': False,
            'allocated_hours': self.qa_allocate_time,
            'date_deadline': self.qa_end_date
        })

        self.qa_task_id = task.id

        if self.qa_team_id:
            self.qa_team_id.write({
                'state': 'working',
                'current_qa_task_id': self.qa_task_id
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'QA Task',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': task.id,
            'target': 'current',
        }

    def action_subcontract_qa_task(self):
        self.ensure_one()

        project = self._get_or_create_project()

        task = self.env['project.task'].create({
            'name': f'QA - {self.name}',
            'project_id': project.id,
            'partner_id': self.qa_subcontractor_id.id,
            'qa_subcontractor_id': self.qa_subcontractor_id.id,
            'task_type': 'qa',
            'is_subcontract': True,
            'allocated_hours': self.qa_allocate_time,
            'date_deadline': self.qa_end_date
        })

        self.qa_task_id = task.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'QA Task',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': task.id,
            'target': 'current',
        }



    def action_view_installation_tasks(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Installation Tasks',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [
                ('project_id', '=', self.project_id.id),
                ('task_type', '=', 'installation'),
            ],
            'context': {
                'default_project_id': self.project_id.id,
            },
        }

    def action_view_qa_tasks(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'QA Tasks',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [
                ('project_id', '=', self.project_id.id),
                ('task_type', '=', 'qa'),
            ],
            'context': {
                'default_project_id': self.project_id.id,
            },
        }

    installation_task_count = fields.Integer(string="Installation Tasks",compute="_compute_task_count")

    qa_task_count = fields.Integer(string="QA Tasks",compute="_compute_task_count")

    @api.depends('project_id')
    def _compute_task_count(self):
        Task = self.env['project.task']
        for rec in self:
            rec.installation_task_count = 0
            rec.qa_task_count = 0

            if rec.project_id:
                rec.installation_task_count = Task.search_count([
                    ('project_id', '=', rec.project_id.id),
                    ('task_type', '=', 'installation'),
                ])

                rec.qa_task_count = Task.search_count([
                    ('project_id', '=', rec.project_id.id),
                    ('task_type', '=', 'qa'),
                ])

    @api.onchange('qa_team_id')
    def _onchange_team(self):
        if self.qa_team_id and self.qa_team_id.state != 'available':
            raise ValidationError(("This team is already assigned to another QA."))


    @api.onchange('installation_team_id')
    def _onchange_team(self):
        if self.installation_team_id and self.installation_team_id.state != 'available':
            raise ValidationError(("This team is already assigned to another Installation."))


    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ren.order') or 'New'

        records = super().create(vals_list)

        records.mapped('installation_team_id').write({
            'state': 'assigned'
        })

        records.mapped('qa_team_id').write({
            'state': 'assigned'
        })

        return records

    def write(self, vals):
        old_installation_teams = self.mapped('installation_team_id')
        old_qa_teams = self.mapped('qa_team_id')

        res = super().write(vals)

        if 'installation_team_id' in vals:
            old_installation_teams.write({'state': 'available'})
            self.mapped('installation_team_id').write({'state': 'assigned'})

        if 'qa_team_id' in vals:
            old_qa_teams.write({'state': 'available'})
            self.mapped('qa_team_id').write({'state': 'assigned'})

        return res