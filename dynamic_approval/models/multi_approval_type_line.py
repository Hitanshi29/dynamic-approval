from odoo import fields, models

APPROVAL_KIND = [
    ('mandatory', 'Mandatory'),
    ('optional', 'Optional'),
]


class MultiApproveTypeLine(models.Model):
    _name = 'multi.approval.type.line'
    _description = 'Approval Type Approver Line'

    approval_type_id = fields.Many2one(
        'multi.approval.type', string='Approval Type',
        required=True, ondelete='cascade'
    )
    title = fields.Char(string='Title',required=True)

    user_id = fields.Many2one(
        'res.users', string='User',required=True,
        domain=lambda self: [
            ('group_ids', 'in', self.env.ref('dynamic_approval.group_access_approval_admin').ids)
        ]
    )

    approval_kind = fields.Selection(
        APPROVAL_KIND, string='Type of Approval', default='mandatory'
    )
    minimum_amount = fields.Float(string="Minimum Amount",required=True)

    def action_view_approver(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.title or 'Approver',
            'res_model': 'multi.approval.type.line',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }