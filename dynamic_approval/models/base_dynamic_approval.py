from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from .multi_approval_type import DYNAMIC_FIELD_NAME 


class Base(models.AbstractModel):
    _inherit = 'base'


    def action_reset_dynamic_approval(self):
        self.ensure_one()

        if 'x_dynamic_approval_pending' in self._fields:
            self.write({
                'x_dynamic_approval_pending': False,
            })

        return True

    def action_request_approval_dynamic(self):
        self.ensure_one()

        ApprovalType = self.env['multi.approval.type'].sudo()

        approval_type = ApprovalType.browse(
            self.env.context.get('approval_type_id')
        )

        if not approval_type.exists():
            raise UserError(_("Approval configuration not found."))

        has_amount_field = 'amount_total' in self._fields
        record_amount = (self.amount_total or 0.0) if has_amount_field else 0.0

        if has_amount_field:
            # A real amount exists on this model — evaluate Min Amount tiers.
            applicable_approvers = approval_type.approver_ids.filtered(
                lambda l: record_amount >= l.minimum_amount
            )
        else:
            # No amount-like field on this model at all (Employee, Stock
            # Picking, ...) — the Min Amount rule can't be evaluated, so we
            # must NOT treat that as "amount is 0" and auto-skip. Approval
            # is always required in this case.
            applicable_approvers = approval_type.approver_ids

        # Nobody needs to approve — only possible when the amount was
        # actually evaluated and came in below every tier.
        if has_amount_field and not applicable_approvers:

            if approval_type.approved_action:
                safe_eval(
                    approval_type.approved_action,
                    {
                        "record": self,
                        "records": self,
                        "env": self.env,
                        "user": self.env.user,
                    },
                    mode="exec",
                )

            self.write({
                DYNAMIC_FIELD_NAME: "resolved",
            })

            self.message_post(
                body=_(
                    "Approval skipped automatically because the order amount (%.2f) "
                    "is below all configured approval limits."
                ) % record_amount
            )

            return True

        action = approval_type.action_request_id.sudo().read()[0]

        ctx = dict(self.env.context)
        ctx.update({
            "active_id": self.id,
            "active_ids": self.ids,
            "active_model": self._name,
        })

        action["context"] = ctx

        return action