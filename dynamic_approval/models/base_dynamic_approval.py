from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

import logging
_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    def action_request_approval_dynamic(self):
        self.ensure_one()

        ApprovalType = self.env['multi.approval.type'].sudo()
        approval_type_id = self.env.context.get('approval_type_id')
        approval_type = ApprovalType.browse(approval_type_id)
        if not approval_type.exists():
            raise UserError(_('Approval configuration not found.'))

        thresholds = approval_type.approver_ids.mapped('minimum_amount')
        threshold = min(thresholds) if thresholds else 0.0
        record_amount = getattr(self, 'amount_total', 0.0) or 0.0

        if record_amount < threshold:
            if approval_type.approved_action:  
                safe_eval(
                    approval_type.approved_action,
                    {'record': self, 'records': self, 'env': self.env, 'user': self.env.user},
                    mode='exec'
                )
            self.message_post(
                body=_('Approval skipped automatically: amount (%s) is below the configured minimum (%s).')
                % (record_amount, threshold)
            )
            return True

        action = approval_type.action_request_id.sudo().read()[0]
        ctx = dict(self.env.context)
        ctx.update({
            'active_id': self.id,
            'active_ids': self.ids,
            'active_model': self._name,
        })
        action['context'] = ctx
        return action