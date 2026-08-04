# -*- coding: utf-8 -*-
# Part of Bizople Solutions Pvt. Ltd.
# Licensed under the Bizople Proprietary License v1.0.
# Copyright (C) 2026 Bizople Solutions Pvt. Ltd.

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

APPROVE_STATE = [
    ('approve','Approve'),
    ('reject','Reject')
]

class SiteInspection(models.Model):
    _name = 'site.inspection'
    _description = 'Site Inspection'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'name'

    name = fields.Char(required=True ,copy=False, readonly=True, index='trigram', default=lambda self: ('New'))

    lead_id = fields.Many2one('crm.lead',string="Lead id",required=True,readonly=True)

    customer_id = fields.Many2one('res.partner',string="Customer",related='lead_id.partner_id',store=True)

    quotation_id = fields.Many2one('sale.order',string="Quotation",readonly=True,compute="_compute_quotation_id")
    
    @api.depends('lead_id')
    def _compute_quotation_id(self):
        for rec in self:
            quotation = self.env['sale.order'].search(
                [('opportunity_id', '=', rec.lead_id.id)],
                order='id desc',
                limit=1
            )
            rec.quotation_id = quotation
 
    company_id = fields.Many2one('res.company',default=lambda self: self.env.company)

    visit_date = fields.Date(string="Date Of Inspection")

    sales_id = fields.Many2one(related="lead_id.user_id",string="Sales Person")

    site_address = fields.Text(string="Site Address")

    site_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial')
    ], string="Site Type")

    
    roof_type = fields.Selection([
        ('rcc', 'RCC'),
        ('metal_sheet', 'Metal Sheet'),
        ('tile', 'Tile'),
        ('other', 'Other')
    ], string="Roof Type")

    roof_area = fields.Float(string="Roof Area (Sq.ft)")

    required_capacity = fields.Float(string="Required Capacity (kW)")
    recommended_capacity = fields.Float(string="Recommended Capacity (kW)")
    
    meter_type = fields.Selection([
        ('single_phase', 'Single Phase'),
        ('three_phase', 'Three Phase')
    ], string="Meter Type")

    average_bill = fields.Float(string="Average Monthly Bill")

    currency_id = fields.Many2one( 'res.currency',related='company_id.currency_id',readonly=True)

    shading_present = fields.Boolean(string="Shading Present")
    shading_details = fields.Text(string="Shading Details")

    
    feasibility = fields.Selection([
        ('feasible', 'Feasible'),
        ('partially_feasible', 'Partially Feasible'),
        ('not_feasible', 'Not Feasible')
    ], string="Feasibility")


    inspection_image_ids = fields.Many2many(
        'ir.attachment',
        'solar_site_inspection_ir_attachment_rel',
        'inspection_id',
        'attachment_id',
        string="Images",
        domain="[('mimetype', 'ilike', 'image')]",
    )

    team_id = fields.Many2one('team.management',string='Team',required=True,domain=[('state', '=', 'available'),('team_type','=','survey_team')])

    team_leader_id = fields.Many2one(related="team_id.leader_id",string="Leader")
    leader_email = fields.Char(related="team_id.leader_id.email",string="Email")

    state = fields.Selection(
        [
            ('draft','Draft'),
            ('in_progress','In Progress'),
            ('done','Done'),
            ('cancel','Cancel')
        ],default='draft',tracking=True,group_expand='_group_expand_states')

    approve_status = fields.Selection(selection = APPROVE_STATE,string="Approve Status")
    
    state_in_approve = fields.Selection(
        selection = APPROVE_STATE + [
            ('draft','Draft'),
            ('in_progress','In Progress'),
            ('done','Done'),
            ('cancel','Cancel')
        ],string="Status",compute='_compute_approve_state')

    @api.depends('approve_status', 'state',)
    def _compute_approve_state(self):
        for move in self:
            if move.state == 'done':
                if move.approve_status in ('approve', 'reject'):
                    move.state_in_approve = move.approve_status

            if not move.state_in_approve:
                move.state_in_approve = move.state

    @api.model
    def _group_expand_states(self, states, domain):
        return [
            'draft',
            'in_progress',
            'done',
            'cancel',
        ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('site.inspection') or 'New'
                
        records = super().create(vals_list)

        records.mapped('team_id').write({
            'state': 'assigned',
        })

        return records

  
    @api.onchange('team_id')
    def _onchange_team(self):
        if self.team_id and self.team_id.state != 'available':
            raise ValidationError(("This team is already assigned to another inspection."))


    def write(self, vals):
        old_teams = self.mapped('team_id')

        res = super().write(vals)

        # search_state = self.env['sale.order'].search([('id','=',self.quotation_id.id),('state','=','draft')])
        # logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>State is %s",search_state)

        if 'team_id' in vals:

            old_teams.write({'state': 'available'})
            self.mapped('team_id').write({'state': 'assigned'})

        return res

    def action_start_work(self):
        for rec in self:
            rec.state = 'in_progress'

            if rec.team_id:
                rec.team_id.sudo().write({
                    'state': 'working',
                    'start_date': fields.Datetime.now(),
                    'completion_date': False,
                })
    
    def action_complete_work(self):
        for rec in self:
            rec.state = 'done'
            rec.approve_status = False

            if rec.team_id:
                rec.team_id.sudo().write({
                    'state': 'completed',
                    'completion_date': fields.Datetime.now(),
                })

    def approve_inspection(self):
        for rec in self:

            rec.approve_status = 'approve'

            # rec.state = 'approve'

            if rec.team_id:
                rec.team_id.sudo().write({
                    'state': 'available',
                    'start_date': False,
                    'completion_date': False,
                })

            # tasks = self.env['project.task'].search([
            #     ('project_id.sale_order_id', '=', rec.quotation_id.id),
            #     ('name', 'in', ['Installation', 'QA'])
            # ])

            # tasks.write({
            #     'inspection_id': rec.id
            # })

    def reject_inspection(self):
        # self.write({'state': 'reject'})
        self.write({'approve_status': 'reject'})

        for rec in self:
            if rec.team_id:
                rec.team_id.sudo().write({
                    'state': 'available',
                    'start_date': False,
                    'completion_date': False,
                })

    def cancel_inspection(self):

        self.write({'state': 'cancel'})

        for rec in self:
            if rec.team_id:
                rec.team_id.sudo().write({
                    'state': 'available',
                    'start_date': False,
                    'completion_date': False,
                })

    def action_set_to_draft(self):
        self.write({'state': 'draft'})
    
    def create_ren_order(self):
        self.ensure_one()

        if not self.quotation_id:
            raise ValidationError("Must Required Sale order so you create first sale order then create REN Order")

        if not self.quotation_id.state == 'sale':
            raise ValidationError("Your Sale Order Is not Confirm So Frist Confirm Order")

        return {
            'type': 'ir.actions.act_window',
            'name': 'REN Order',
            'res_model': 'ren.order',
            'view_mode': 'form,list',
            'context': {
                'default_customer_id': self.customer_id.id,
                'default_lead_id': self.lead_id.id,
                'default_quotation_id': self.quotation_id.id,
                'default_quotation_amount': self.quotation_id.amount_total,
                'default_site_inspection_id': self.id,
            }
        }

    order_count = fields.Integer(compute='_compute_counts')
    def _compute_counts(self):
        for rec in self:
            rec.order_count = self.env['ren.order'].search_count([('site_inspection_id', '=', rec.id)])


    def action_report_site_inspection(self):
        self.ensure_one()
        return self.env.ref('solar_energy_management_biz.action_report_site_inspection').report_action(self)


    def action_send_email(self):
        self.ensure_one()

        template = self.env.ref(
            'solar_energy_management_biz.inspection_email_template'
        )

        compose_form = self.env.ref('mail.email_compose_message_wizard_form')

        return {
            # '_name': 'Send Confirmation Email',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'view_id': compose_form.id,
            'target': 'new',
            'context': {
                'default_model': 'site.inspection',
                'default_res_ids': [self.id],
                'default_template_id': template.id,
                'default_use_template': True,
                'default_partner_ids': [(6, 0, [self.customer_id.id])],  
                'force_email': True,
            },
        }

    def action_view_ren_order(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'REN Order',
            'res_model': 'ren.order',
            'view_mode': 'list,form',
            'domain': [('site_inspection_id', '=', self.id)],
        }

    checklist_template_ids = fields.Many2many('checklist.template',string="Template Name", domain=[('checklist_type', '=', 'survey_template')])

    all_checklist_line_ids = fields.One2many(
        'site.inspection.checklist','inspection_id'
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