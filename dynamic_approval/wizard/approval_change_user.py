from odoo import fields, models, _


class ApprovalChangeApproverWizard(models.TransientModel):
    _name = 'approval.change.user.wizard'
    _description = 'Change Approver Wizard'

    request_id = fields.Many2one('approval.request', string='Request', required=True)
    new_approver_id = fields.Many2one(
        'res.users', string='New Approver', required=True,
        domain=lambda self: [
            ('group_ids', 'in', self.env.ref('dynamic_approval.group_access_approval_admin').ids)
        ]
    )
    reason = fields.Text(string='Reason',required=True)

    def action_update(self):
            self.ensure_one()
            old_approver = self.request_id.approver_id
            self.request_id.approver_id = self.new_approver_id

            active_line = self.request_id.line_ids.filtered(lambda l: l.state == 'to_approve')[:1]
            if active_line:
                active_line.user_id = self.new_approver_id.id

            body = _('Approver changed from %(old)s to %(new)s.') % {
                'old': old_approver.name or _('(none)'),
                'new': self.new_approver_id.name,
            }
            if self.reason:
                body += _('<br/>Reason: %s') % self.reason
            self.request_id.message_post(body=body)

            return {'type': 'ir.actions.act_window_close'}