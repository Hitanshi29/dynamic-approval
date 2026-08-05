from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.fields import Domain

import logging
_logger = logging.getLogger(__name__)


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(required=True, copy=False, readonly=True, index='trigram', default=lambda self: ('New'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('approval.request') or 'New'

            if vals.get('type_id') and 'type_document_opt' not in vals:
                type_rec = self.env['multi.approval.type'].browse(vals['type_id'])
                vals.update({
                    'type_document_opt': type_rec.document_opt or 'none',
                    'type_contact_opt': type_rec.contact_opt or 'none',
                    'type_date_opt': type_rec.date_opt or 'none',
                    'type_period_opt': type_rec.period_opt or 'none',
                    'type_item_opt': type_rec.item_opt or 'none',
                    'type_multi_items_opt': type_rec.multi_items_opt or 'none',
                    'type_quantity_opt': type_rec.quantity_opt or 'none',
                    'type_amount_opt': type_rec.amount_opt or 'none',
                    'type_payment_opt': type_rec.payment_opt or 'none',
                    'type_reference_opt': type_rec.reference_opt or 'none',
                    'type_location_opt': type_rec.location_opt or 'none',
                })
        records = super().create(vals_list)
        for rec in records:
            if rec.type_id and rec.state == 'draft':
                rec._build_approval_lines()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('type_id', 'record_amount', 'amount')):
            for rec in self:
                if rec.state == 'draft' and rec.type_id:
                    rec._build_approval_lines()
        return res

    title = fields.Char(string='Title', required=True, tracking=True, copy=False)

    request_by = fields.Many2one(
        'res.users', string='Request by', required=True, tracking=True,
        default=lambda self: self.env.user)

    request_date = fields.Datetime(
        string='Request Date', required=True, tracking=True,
        default=fields.Datetime.now)

    type_id = fields.Many2one(
        'multi.approval.type', string='Type', tracking=True)

    deadline = fields.Date(string='Deadline', tracking=True)

    approver_id = fields.Many2one(
        'res.users', string='Approver', required=True, tracking=True)

    allowed_approver_user_ids = fields.Many2many(
        'res.users', compute='_compute_allowed_approver_user_ids',
        string='Allowed Approvers')

    @api.depends('type_id.approver_ids.user_id')
    def _compute_allowed_approver_user_ids(self):
        for rec in self:
            rec.allowed_approver_user_ids = rec.type_id.approver_ids.mapped('user_id')

    description = fields.Html(string='Description')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('cancel', 'Cancel'),
    ], string='Status', default='draft', tracking=True, copy=False)

    res_model = fields.Char(string='Related Document Model')
    res_id = fields.Integer(string='Related Document ID')
    res_name = fields.Char(string='Related Document Name')

    is_approver = fields.Boolean(string='Is Approver', compute='_compute_is_approver')

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)

    record_amount = fields.Float(string='Record Amount')

    amount_evaluable = fields.Boolean(
        string='Amount Rule Evaluable', default=True,
        help='False when the source document has no amount-like field at all '
            '(e.g. a Stock Picking) — Min Amount tiers cannot be evaluated, '
            'so only the lowest configured tier is required.')

    line_ids = fields.One2many(
        'approval.request.line', 'request_id', string='Approval Steps')


    document = fields.Binary(string='Document', attachment=True)
    document_filename = fields.Char(string='Document Filename')
    contact_id = fields.Many2one('res.partner', string='Contact')
    date = fields.Date(string='Date')
    date_from = fields.Date(string='Period From')
    date_to = fields.Date(string='Period To')
    item = fields.Char(string='Item')
    item_ids = fields.One2many(
        'approval.request.item.line', 'request_id', string='Items')
    quantity = fields.Float(string='Quantity')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    payment_ref = fields.Char(string='Payment Reference')
    reference = fields.Char(string='Reference')
    location = fields.Char(string='Location')

    

    FIELD_OPTIONS = [
        ('required', 'Required'),
        ('optional', 'Optional'),
        ('none', 'None'),
    ]

    type_document_opt = fields.Selection(FIELD_OPTIONS, string='Document Opt', default='none')
    type_contact_opt = fields.Selection(FIELD_OPTIONS, string='Contact Opt', default='none')
    type_date_opt = fields.Selection(FIELD_OPTIONS, string='Date Opt', default='none')
    type_period_opt = fields.Selection(FIELD_OPTIONS, string='Period Opt', default='none')
    type_item_opt = fields.Selection(FIELD_OPTIONS, string='Item Opt', default='none')
    type_multi_items_opt = fields.Selection(FIELD_OPTIONS, string='Multi Items Opt', default='none')
    type_quantity_opt = fields.Selection(FIELD_OPTIONS, string='Quantity Opt', default='none')
    type_amount_opt = fields.Selection(FIELD_OPTIONS, string='Amount Opt', default='none')
    type_payment_opt = fields.Selection(FIELD_OPTIONS, string='Payment Opt', default='none')
    type_reference_opt = fields.Selection(FIELD_OPTIONS, string='Reference Opt', default='none')
    type_location_opt = fields.Selection(FIELD_OPTIONS, string='Location Opt', default='none')

    _TYPE_OPT_FIELD_MAP = {
        'type_document_opt': 'document_opt',
        'type_contact_opt': 'contact_opt',
        'type_date_opt': 'date_opt',
        'type_period_opt': 'period_opt',
        'type_item_opt': 'item_opt',
        'type_multi_items_opt': 'multi_items_opt',
        'type_quantity_opt': 'quantity_opt',
        'type_amount_opt': 'amount_opt',
        'type_payment_opt': 'payment_opt',
        'type_reference_opt': 'reference_opt',
        'type_location_opt': 'location_opt',
    }

    @api.onchange('type_id')
    def _onchange_type_id_snapshot_opts(self):
        """Only fires while the record is a draft being edited in the UI
        (picking/changing the Type). Copies the Approval Type's CURRENT
        Fields Setting onto this request. Once saved, this snapshot no
        longer moves even if the Approval Type is edited afterwards."""
        for rec in self:
            t = rec.type_id
            for req_field, type_field in rec._TYPE_OPT_FIELD_MAP.items():
                rec[req_field] = t[type_field] if t else 'none'


    @api.depends('approver_id', 'line_ids.state', 'line_ids.user_id')
    def _compute_is_approver(self):
        uid = self.env.uid
        for rec in self:
            active_line = rec.line_ids.filtered(lambda l: l.state == 'to_approve')[:1]
            rec.is_approver = (active_line.user_id.id if active_line else rec.approver_id.id) == uid


    @api.model
    def _open_request_wizard(self, res_model, res_id, type_id):
        approval_type = self.env['multi.approval.type'].browse(type_id)
        record = self.env[res_model].browse(res_id)

        if approval_type.domain and approval_type.domain != '[]':
            domain = safe_eval(approval_type.domain)
            final_domain = Domain.AND([
                [('id', '=', res_id)],
                domain,
            ])
            if not self.env[res_model].search_count(final_domain):
                raise UserError(
                    _('This record does not currently meet the approval conditions.')
                )

        previous = self.search([
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
            ('type_id', '=', type_id),
            ('state', '=', 'cancel'),
        ], order='id desc', limit=1)

        if previous:
            previous._resume_after_refusal()
            quick_view = self.env.ref('dynamic_approval.view_approval_request_quick_form')
            return {
                'type': 'ir.actions.act_window',
                'name': _('Request Approval'),
                'res_model': 'approval.request',
                'view_mode': 'form',
                'views': [(quick_view.id, 'form')],
                'res_id': previous.id,
                'target': 'new',
            }

        approver_line = approval_type.approver_ids.filtered(
            lambda l: l.approval_kind == 'mandatory' and l.user_id
        )[:1] or approval_type.approver_ids.filtered(lambda l: l.user_id)[:1]
        default_approver = approver_line.user_id.id if approver_line else False

        default_description = approval_type._render_description(record)
        # record_amount = getattr(record, 'amount_total', 0.0) or 0.0
        has_amount_field = 'amount_total' in record._fields
        record_amount = (record.amount_total or 0.0) if has_amount_field else 0.0

        quick_view = self.env.ref('dynamic_approval.view_approval_request_quick_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Approval'),
            'res_model': 'approval.request',
            'view_mode': 'form',
            'views': [(quick_view.id, 'form')],
            'target': 'new',
            'context': {
                'default_res_model': res_model,
                'default_res_id': res_id,
                'default_res_name': record.display_name,
                'default_title': record.display_name,
                'default_type_id': type_id,
                'default_approver_id': default_approver,
                'default_description': default_description,
                'default_record_amount': record_amount,
                'default_amount_evaluable': has_amount_field,
            },
        }

    @api.model
    def _open_existing_request(self, res_model, res_id, type_id):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval Request'),
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', res_model),
                ('res_id', '=', res_id),
                ('type_id', '=', type_id),
            ],
            'target': 'current',
        }

    def _set_dynamic_flag(self, value):
        self.ensure_one()
        if not (self.res_model and self.res_id):
            return
        target_model = self.env[self.res_model]
        if 'x_dynamic_approval_pending' in target_model._fields:
            target_model.sudo().browse(self.res_id).write({'x_dynamic_approval_pending': value})

   
    def _run_type_action(self, field_name):
        self.ensure_one()
        code = getattr(self.type_id, field_name, False)
        if not code or not (self.res_model and self.res_id):
            return

        if not self.env['ir.model.access'].check(self.res_model, 'write', raise_exception=False):
            raise UserError(_(
                "You don't have access to this module, so you can't approve or cancel this request."
            ))

        record = self.env[self.res_model].sudo().browse(self.res_id)
        if not record.exists():
            return
        try:
            safe_eval(code, {'record': record, 'env': record.env}, mode='exec')
        except Exception as e:
            raise UserError(_('The configured action for "%s" failed: %s') % (self.type_id.name, e))

    def _check_dynamic_required_fields(self):
        """Server-side mirror of the view's required= domains, so a
        'Required' Fields Setting on the Approval Type can't be bypassed
        by submitting through another view, an import, or a call from
        code."""
        self.ensure_one()
        checks = [
            ('document', 'type_document_opt', _('Document')),
            ('contact_id', 'type_contact_opt', _('Contact')),
            ('date', 'type_date_opt', _('Date')),
            ('item', 'type_item_opt', _('Item')),
            ('quantity', 'type_quantity_opt', _('Quantity')),
            ('amount', 'type_amount_opt', _('Amount')),
            ('payment_ref', 'type_payment_opt', _('Payment Reference')),
            ('reference', 'type_reference_opt', _('Reference')),
            ('location', 'type_location_opt', _('Location')),
        ]
        missing = []
        for field_name, opt_name, label in checks:
            if getattr(self, opt_name) == 'required' and not self[field_name]:
                missing.append(label)
        if self.type_period_opt == 'required' and not (self.date_from and self.date_to):
            missing.append(_('Period'))
        if self.type_multi_items_opt == 'required' and not self.item_ids:
            missing.append(_('Items'))
        if missing:
            raise UserError(_('Please fill in the required field(s): %s') % ', '.join(missing))


    # def _get_applicable_approver_tiers(self):
    #     self.ensure_one()
    #     type_lines = self.type_id.approver_ids.filtered(lambda l: l.user_id)
    #     if not type_lines:
    #         return type_lines
    #     amount = self.record_amount or self.amount or 0.0
    #     matching = type_lines.filtered(
    #         lambda l: amount >= (l.minimum_amount or 0.0)
    #     ).sorted(key=lambda l: l.minimum_amount or 0.0)
    #     if matching:
    #         return matching
    
    #     return type_lines.sorted(key=lambda l: l.minimum_amount or 0.0)[:1]

    def _get_applicable_approver_tiers(self):
        self.ensure_one()
        type_lines = self.type_id.approver_ids.filtered(lambda l: l.user_id)
        if not type_lines:
            return type_lines

        sorted_lines = type_lines.sorted(key=lambda l: l.minimum_amount or 0.0)

        if not self.amount_evaluable:
            # No amount-like field on the source document at all (e.g. a
            # Stock Picking) — the Min Amount rule can't be evaluated, so
            # only the base/lowest tier applies; higher amount-gated tiers
            # are skipped.
            return sorted_lines[:1]

        amount = self.record_amount or self.amount or 0.0
        # Cumulative: every tier whose minimum the amount meets or exceeds is
        # required. If the amount is below every tier's minimum, nothing is
        # required at all.
        return sorted_lines.filtered(lambda l: amount >= (l.minimum_amount or 0.0))

    def _build_approval_lines(self):
        self.ensure_one()
        self.line_ids.unlink()

        applicable = self._get_applicable_approver_tiers()
        if not applicable:
            return

        vals_list = []
        for idx, line in enumerate(applicable):
            vals_list.append({
                'request_id': self.id,
                'sequence': (idx + 1) * 10,
                'title': line.title or _('Approval %s') % (idx + 1),
                'user_id': line.user_id.id,
                'minimum_amount': line.minimum_amount,
                'state': 'to_approve' if idx == 0 else 'waiting',
            })
        self.env['approval.request.line'].create(vals_list)
        self.approver_id = applicable[0].user_id.id

    def _resume_after_refusal(self):
        """Bring a REFUSED request back to draft, but keep every step that
        was already approved before the refusal. Only the step that refused
        it (and any steps after it) get asked for again."""
        self.ensure_one()

        cancelled_line = self.line_ids.filtered(lambda l: l.state == 'cancel').sorted('sequence')[:1]

        if not cancelled_line:
            # No per-line info (legacy single-approver flow) — full reset.
            self.line_ids.unlink()
            self._build_approval_lines()
        else:
            redo_lines = self.line_ids.filtered(lambda l: l.sequence >= cancelled_line.sequence)
            redo_lines[0].write({'state': 'to_approve', 'approved_date': False})
            (redo_lines - redo_lines[0]).write({'state': 'waiting', 'approved_date': False})
            self.approver_id = redo_lines[0].user_id.id

        self.state = 'draft'
        self._set_dynamic_flag(False)
        self.message_post(
            body=_('Request reopened after refusal — resuming with %s.') % self.approver_id.name
        )

    @api.onchange('type_id', 'record_amount', 'amount')
    def _onchange_preview_approver_lines(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            applicable = rec._get_applicable_approver_tiers()
            commands = [(5, 0, 0)]
            for idx, line in enumerate(applicable):
                commands.append((0, 0, {
                    'sequence': (idx + 1) * 10,
                    'title': line.title or _('Approval %s') % (idx + 1),
                    'user_id': line.user_id.id,
                    'minimum_amount': line.minimum_amount,
                    'state': 'to_approve' if idx == 0 else 'waiting',
                }))
            rec.line_ids = commands

    def _post_message_on_source_record(self, body):
        """Post a chatter note on the actual business document (e.g. the
        Purchase Order), not on the approval.request. Generic — works for
        ANY res_model as long as it inherits mail.thread, so no per-model
        inheritance is needed in this module."""
        self.ensure_one()
        if not (self.res_model and self.res_id):
            return
        target_model = self.env[self.res_model]
        if 'message_post' not in target_model._fields and not hasattr(target_model, 'message_post'):
            return
        record = target_model.sudo().browse(self.res_id)
        if record.exists():
            record.message_post(body=body)

    def action_submit(self):
        for rec in self:
            rec._check_dynamic_required_fields()

            already_approved = rec.line_ids.filtered(lambda l: l.state == 'approved')
            if already_approved:
                pending = rec.line_ids.filtered(lambda l: l.state != 'approved').sorted('sequence')
                if pending:
                    pending[0].state = 'to_approve'
                    (pending - pending[0]).write({'state': 'waiting'})
                    rec.approver_id = pending[0].user_id.id
            else:
                rec._build_approval_lines()

            # No configured tier's Min Amount was met — nothing to approve.
            if not rec.line_ids and rec.type_id.approver_ids:
                rec.state = 'approved'
                rec._run_type_action('approved_action')
                rec._set_dynamic_flag('approved')
                rec.message_post(body=_('No approval required — amount is below every configured tier.'))
                rec._post_message_on_source_record(
                    _('No approval required for "%s" — amount is below every configured tier.') % rec.type_id.name
                )
                continue

            if not rec.approver_id:
                raise UserError(_('Please select an Approver before submitting.'))

            rec.state = 'submitted'
            rec.message_post(body=_('Approval created'))
            rec._set_dynamic_flag('submitted')
            rec._send_status_mail('mail_template_approval_step_assigned')
            rec._post_message_on_source_record(
                _('Approval requested — "%s" (waiting on %s).') % (rec.type_id.name, rec.approver_id.name)
            )


    def action_approve(self):
        for rec in self:
            active_line = rec.line_ids.filtered(lambda l: l.state == 'to_approve')[:1]

            if active_line:
                if active_line.user_id.id != self.env.uid:
                    raise UserError(_('Only the assigned approver can approve this step.'))
                active_line.write({'state': 'approved', 'approved_date': fields.Datetime.now()})
                rec.message_post(body=_('Step "%s" approved by %s.') % (active_line.title, active_line.user_id.name))
                rec._post_message_on_source_record(
                    _('Approval step "%s" approved by %s.') % (active_line.title, active_line.user_id.name)
                )

                next_line = rec.line_ids.filtered(lambda l: l.state == 'waiting')[:1]
                if next_line:
                    next_line.state = 'to_approve'
                    rec.approver_id = next_line.user_id.id
                    rec._send_status_mail('mail_template_approval_step_assigned')                              # notify the NEXT approver
                    rec._send_status_mail('mail_template_approval_approved', recipient_user=rec.request_by)     # NEW: notify the requester of progress
                    rec._post_message_on_source_record(
                        _('%s -> %s(Approver)') % (active_line.user_id.name, next_line.user_id.name)
                    )
                    continue

                rec.state = 'approved'
                rec._run_type_action('approved_action')
                rec._set_dynamic_flag('approved')
                rec._send_status_mail('mail_template_approval_approved', recipient_user=rec.request_by)
                rec._post_message_on_source_record(
                    _('Approval "%s" fully approved. Last step by %s.') % (rec.type_id.name, active_line.user_id.name)
                )
                continue

            if rec.approver_id.id != self.env.uid:
                raise UserError(_('Only the assigned approver can approve this request.'))
            rec.state = 'approved'
            rec._run_type_action('approved_action')
            rec._set_dynamic_flag('approved')
            rec._send_status_mail('mail_template_approval_approved', recipient_user=rec.request_by)
            rec._post_message_on_source_record(
                _('Approval "%s" approved by %s.') % (rec.type_id.name, rec.approver_id.name)
            )
    
    def action_cancel(self):
        for rec in self:
            active_line = rec.line_ids.filtered(lambda l: l.state == 'to_approve')[:1]

            if active_line:
                if active_line.user_id.id != self.env.uid:
                    raise UserError(_('Only the assigned approver can refuse this step.'))
                active_line.state = 'cancel'
                rec.line_ids.filtered(lambda l: l.state == 'waiting').write({'state': 'cancel'})
                rec.state = 'cancel'
                rec._run_type_action('refused_action')
                rec._set_dynamic_flag('rejected')
                rec._send_status_mail('mail_template_approval_refused', recipient_user=rec.request_by)
                rec.message_post(body=_('Step "%s" cancel by %s.') % (active_line.title, active_line.user_id.name))
                rec._post_message_on_source_record(
                    _('Approval "%s" was cancel at step "%s" by %s.') % (
                        rec.type_id.name, active_line.title, active_line.user_id.name
                    )
                )
                continue

            if rec.approver_id.id != self.env.uid:
                raise UserError(_('Only the assigned approver can cancel this request.'))
            rec.state = 'cancel'
            rec._run_type_action('refused_action')
            rec._set_dynamic_flag('rejected')
            rec._send_status_mail('mail_template_approval_refused', recipient_user=rec.request_by)
            rec.message_post(body=_('Request cancel by %s.') % rec.approver_id.name)
            rec._post_message_on_source_record(
                _('Approval "%s" was cancel by %s.') % (rec.type_id.name, rec.approver_id.name)
            )

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_attach_document(self, attachment_ids):
        self.ensure_one()
        self.message_post(
            body=_('Document(s) attached.'),
            attachment_ids=attachment_ids,
        )

    def _send_status_mail(self, template_xmlid, recipient_user=None):
        try:
            self._send_status_mail_impl(template_xmlid, recipient_user)
        except Exception:
            _logger.exception(
                'Failed to send approval status mail (%s) for %s',
                template_xmlid, self.name
            )

    def _send_status_mail_impl(self, template_xmlid, recipient_user=None):
        self.ensure_one()
        template = self.env.ref('dynamic_approval.%s' % template_xmlid, raise_if_not_found=False)
        if not template:
            return

        recipient_user = recipient_user or self.approver_id

        if recipient_user.email:
            try:
                template.send_mail(
                    self.id,
                    force_send=True,
                    email_values={
                        'email_to': recipient_user.email,
                        # 'email_from': self.env.company.email or self.env.user.email,
                        # 'email_from': 'drashti.patel165@gmail.com',
                        'auto_delete': False,
                    },
                )
                return
            except Exception:
                _logger.exception(
                    'send_mail failed for template %s on %s — falling back to a chatter note.',
                    template_xmlid, self.name
                )

        subject = template._render_field('subject', self.ids)[self.id]
        body = template._render_field('body_html', self.ids)[self.id]
        self.message_post(
            body=body,
            subject=subject,
            subtype_xmlid='mail.mt_comment',
            partner_ids=recipient_user.partner_id.ids,
        )
        if not recipient_user.email:
            _logger.warning(
                'Recipient %s has no email set; status mail (%s) not sent for %s',
                recipient_user.name, template_xmlid, self.name
            )