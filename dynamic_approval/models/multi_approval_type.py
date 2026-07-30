from odoo import models, fields, api, _
from odoo.exceptions import UserError
from lxml import etree   # add this import at the top of the file, with the other imports

# The one field that gets created (once) on whichever model you configure.
# It's what the generated buttons/banner check to decide what to show.
DYNAMIC_FIELD_NAME = 'x_dynamic_approval_pending'


class MultiApprovalType(models.Model):
    _name = 'multi.approval.type'
    _description = 'Approval Type'

    name = fields.Char(string="Name", required=True)
    description = fields.Char(string="Description")
    image = fields.Image(string="Photo")
    is_model = fields.Boolean(string="Apply For Model")
    is_configured = fields.Boolean(string="Is Configured", default=False)

    model_id = fields.Many2one(
        'ir.model', string='Related Model',
        domain=[
            ('transient', '=', False),
            # ('model', 'not like', 'ir.%'),
            # ('model', 'not like', 'base.%'),
        ],
        help='Model this approval type applies to.',
        ondelete='cascade',
    )
    model_name = fields.Char(
        string='Model Name', related='model_id.model', store=True, readonly=True,
    )

    approver_ids = fields.One2many(
        'multi.approval.type.line', 'approval_type_id', string='Approvers'
    )

    domain = fields.Char(
        string='Domain', default='[]',
        help='Filter used to match records this rule applies to.'
    )

    hide_buttons_from_model_view = fields.Boolean(
        string='Hide Buttons from Model View?',
        help='If checked, the record\'s own workflow buttons are hidden while approval is pending.'
    )

    approved_action = fields.Text(
        string='Approved Action',
        help='Python executed on the record when approved. Use "record" for the document.'
    )
    refused_action = fields.Text(
        string='Refused Action',
        help='Python executed on the record when refused. Use "record" for the document.'
    )

    # bookkeeping — lets us find and delete everything we generated
    generated_view_id = fields.Many2one('ir.ui.view', string='Generated View', readonly=True, copy=False)
    generated_field_id = fields.Many2one('ir.model.fields', string='Generated Field', readonly=True, copy=False)
    action_request_id = fields.Many2one('ir.actions.server', string='Request Action', readonly=True, copy=False)
    action_view_id = fields.Many2one('ir.actions.server', string='View Action', readonly=True, copy=False)

    to_review_count = fields.Integer(string="To Review Count", compute="_compute_to_review_count")

    def _compute_to_review_count(self):
        for rec in self:
            rec.to_review_count = self.env['approval.request'].search_count([
                ('type_id', '=', rec.id),
                ('state', '=', 'submitted'),
            ])

            
    def action_create_request(self):
        """Called from the 'Create Request' button on the kanban card. Only for types
        WITHOUT a Model (is_model = False) — the Contact/Sale Approval/
        Purchase Order cards in your kanban, as long as their model isn't
        selected. Opens the full Approval Request form pre-filled."""
        self.ensure_one()
        if self.is_model:
            raise UserError(_(
                'This Approval Type is linked to a Model (%s). Use the '
                '"Request Approval" button on the record itself instead.'
            ) % (self.model_name or ''))

        approver_line = self.approver_ids.filtered(
            lambda l: l.approval_kind == 'mandatory' and l.user_id
        )[:1] or self.approver_ids.filtered(lambda l: l.user_id)[:1]
        default_approver = approver_line.user_id.id if approver_line else False

        # NEW — no target record exists for a no-Model type, so pass
        # record=False; _render_description() now handles that.
        default_description = self._render_description(False)

        return {
            'name': _('New Approval Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'form',
            'view_id': self.env.ref('dynamic_approval.view_approval_request_form').id,
            'target': 'current',
            'context': {
                'default_type_id': self.id,
                'default_title': self.name,
                'default_approver_id': default_approver,
                'default_description': default_description,
            },
        }


    def action_view_requests_to_review(self):
        self.ensure_one()
        return {
            'name': 'To Review',
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('type_id', '=', self.id), ('state', '=', 'submitted')],
            'context': {'default_type_id': self.id},
        }

    # ------------------------------------------------------------------
    # CONFIGURE — this is the method your existing "Configure" button
    # already calls. It now builds the field, the two generic actions,
    # and the inherited view, for whatever model was picked.
    # ------------------------------------------------------------------
    def action_configure(self):
        self.ensure_one()
        if not self.model_id:
            raise UserError(_('Select a Model first.'))

        self.sudo()._ensure_marker_field()
        self.sudo()._ensure_server_actions()
        self.sudo()._ensure_generated_view()
        self.is_configured = True
        return True

    def action_unconfigure(self):
        self.ensure_one()
        self.sudo()._cleanup_generated_records()
        self.is_configured = False
        return True

    def unlink(self):
        for rec in self:
            rec.sudo()._cleanup_generated_records()
        return super().unlink()

    def _cleanup_generated_records(self):
        self.ensure_one()
        self.generated_view_id.unlink()
        self.action_request_id.unlink()
        self.action_view_id.unlink()
        # the field itself is left in place — another Approval Type on the
        # same model may still be using it, and dropping a column that
        # holds data is not something to do silently.

    def _ensure_marker_field(self):
        """Create the boolean field on the target model, once, via the
        same mechanism Studio uses — no per-model Python needed."""
        self.ensure_one()
        Fields = self.env['ir.model.fields'].sudo()
        existing = Fields.search([
            ('model_id', '=', self.model_id.id),
            ('name', '=', DYNAMIC_FIELD_NAME),
        ], limit=1)
        if existing:
            self.generated_field_id = existing.id
            return existing
        field = Fields.create({
            'name': DYNAMIC_FIELD_NAME,
            'field_description': 'Approval Pending',
            'model_id': self.model_id.id,
            'ttype': 'boolean',
            'copied': False,
        })
        self.generated_field_id = field.id
        return field

    def _ensure_server_actions(self):
        """Two tiny server actions bound to the target model. Their code
        only ever calls into approval.request — a fixed, known model —
        so the same two snippets work for ANY target model."""
        self.ensure_one()
        Actions = self.env['ir.actions.server'].sudo()

        if not self.action_request_id:
            self.action_request_id = Actions.create({
                'name': 'Request Approval (%s)' % self.name,
                'model_id': self.model_id.id,
                'state': 'code',
                'code': (
                    "action = env['approval.request']._open_request_wizard("
                    "record._name, record.id, %d)" % self.id
                ),
            })

        if not self.action_view_id:
            self.action_view_id = Actions.create({
                'name': 'View Approval (%s)' % self.name,
                'model_id': self.model_id.id,
                'state': 'code',
                'code': (
                    "action = env['approval.request']._open_existing_request("
                    "record._name, record.id, %d)" % self.id
                ),
            })

    def _domain_fields_and_expr(self, domain_str):
        """Turns a simple AND-only domain like [('state','=','draft')] into
        a boolean expression the view can evaluate live in the browser
        (e.g. state == 'draft'), plus the field names it needs declared in
        the arch. Anything more complex (OR, nested domains) safely falls
        back to 'always eligible' here — the real check still happens
        server-side in _open_request_wizard, so nothing is bypassed."""
        import ast
        try:
            domain = ast.literal_eval(domain_str or '[]')
        except Exception:
            return [], 'True'
        if not domain:
            return [], 'True'

        ops = {'=': '==', '!=': '!=', 'in': 'in', 'not in': 'not in',
               '>': '>', '<': '<', '>=': '>=', '<=': '<='}
        fields_used, parts = [], []
        for leaf in domain:
            if not (isinstance(leaf, (list, tuple)) and len(leaf) == 3):
                return [], 'True'
            field, op, value = leaf
            if op not in ops:
                return [], 'True'
            fields_used.append(field)
            parts.append("%s %s %r" % (field, ops[op], value))
        return fields_used, ' and '.join(parts)


    def _ensure_generated_view(self):
        self.ensure_one()
        Views = self.env['ir.ui.view'].sudo()

        base_view = Views.search([
            ('model', '=', self.model_name),
            ('type', '=', 'form'),
            ('mode', '=', 'primary'),
        ], order='priority', limit=1)
        if not base_view:
            raise UserError(_('No form view found for model %s.') % self.model_name)

        req_action_id = self.action_request_id.id
        view_action_id = self.action_view_id.id
        req_name = str(req_action_id)
        view_name = str(view_action_id)

        fields_used, eligible_expr = self._domain_fields_and_expr(self.domain)

        data = etree.Element('data')

        # --- Request Approval / View Approval buttons + marker fields ---
        header_xpath = etree.SubElement(data, 'xpath')
        header_xpath.set('expr', "//form/header")
        header_xpath.set('position', 'inside')

        marker_field = etree.SubElement(header_xpath, 'field')
        marker_field.set('name', DYNAMIC_FIELD_NAME)
        marker_field.set('invisible', '1')

        for f in dict.fromkeys(fields_used):
            fld = etree.SubElement(header_xpath, 'field')
            fld.set('name', f)
            fld.set('invisible', '1')

        # req_btn = etree.SubElement(header_xpath, 'button')
        # req_btn.set('name', req_name)
        # req_btn.set('type', 'object')
        # req_btn.set('string', 'Request Approval')
        # req_btn.set('class', 'oe_highlight')
        # req_btn.set('invisible', '%s or not (%s)' % (DYNAMIC_FIELD_NAME, eligible_expr))
        # req_btn.set('context', "{'approval_type_id': %d}" % self.id)

        req_btn = etree.SubElement(header_xpath, 'button')
        req_btn.set('name', 'action_request_approval_dynamic')   # was: req_name / type="action"
        req_btn.set('type', 'object')
        req_btn.set('string', 'Request Approval')
        req_btn.set('class', 'oe_highlight')
        req_btn.set('invisible', '%s or not (%s)' % (DYNAMIC_FIELD_NAME, eligible_expr))
        req_btn.set('context', "{'approval_type_id': %d}" % self.id)

        view_btn = etree.SubElement(header_xpath, 'button')
        view_btn.set('name', view_name)
        view_btn.set('type', 'action')
        view_btn.set('string', 'View Approval')
        view_btn.set('invisible', 'not %s' % DYNAMIC_FIELD_NAME)

        # --- Hide the model's own header buttons while the record matches
        #     the configured Domain (e.g. state == 'draft' / "Quotation") ---
        if self.hide_buttons_from_model_view and eligible_expr != 'True':
            # IMPORTANT: use the fully RESOLVED arch (all inherited views applied),
            # not just base_view.arch_db, otherwise buttons added by other
            # modules (sale_management, account, etc.) are invisible to us
            # and never get hidden -> native Confirm/Cancel keep showing.
            try:
                resolved = self.env[self.model_name].get_view(
                    view_id=base_view.id, view_type='form'
                )
                arch_root = etree.fromstring(resolved['arch'].encode())
            except Exception:
                arch_root = None

            header_node = arch_root.find('.//header') if arch_root is not None else None
            if header_node is not None:
                seen_positions = {}  # name -> occurrence count, to build unique xpaths
                for btn in header_node.findall('button'):
                    name = btn.get('name')
                    if not name or name in (req_name, view_name):
                        continue

                    seen_positions[name] = seen_positions.get(name, 0) + 1
                    occurrence = seen_positions[name]

                    # Handle both the modern `invisible` domain and the legacy
                    # `states="draft,sent"` attribute. If we only add `invisible`
                    # while `states` is still present, Odoo honors BOTH rules
                    # independently and the button can still show -> this is
                    # the most likely cause of buttons showing "twice"/not hiding.
                    states_attr = btn.get('states')
                    existing_invisible = (btn.get('invisible') or '0').strip()

                    if states_attr:
                        state_list = [s.strip() for s in states_attr.split(',') if s.strip()]
                        if state_list:
                            states_expr = "state not in %r" % (state_list,)
                            existing_invisible = (
                                '(%s) or (%s)' % (existing_invisible, states_expr)
                                if existing_invisible != '0' else states_expr
                            )

                    combined = '(%s) or (%s)' % (existing_invisible, eligible_expr)

                    # Target this exact button occurrence (in case the same
                    # `name` appears more than once in the resolved arch, e.g.
                    # duplicated per state-branch) so we don't accidentally
                    # touch the wrong node or skip one.
                    btn_xpath = etree.SubElement(data, 'xpath')
                    btn_xpath.set(
                        'expr',
                        "//form/header/button[@name='%s'][%d]" % (name, occurrence)
                    )
                    btn_xpath.set('position', 'attributes')

                    attr = etree.SubElement(btn_xpath, 'attribute')
                    attr.set('name', 'invisible')
                    attr.text = combined

                    if states_attr:
                        # Neutralize the legacy states attribute so it can no
                        # longer force the button visible on its own.
                        attr2 = etree.SubElement(btn_xpath, 'attribute')
                        attr2.set('name', 'states')
                        # leave empty text -> removes the attribute's effect

        # --- "Waiting Approval" banner ---
        sheet_xpath = etree.SubElement(data, 'xpath')
        sheet_xpath.set('expr', "//form/sheet")
        sheet_xpath.set('position', 'before')

        banner = etree.SubElement(sheet_xpath, 'div')
        banner.set('class', 'alert alert-info')
        banner.set('role', 'alert')
        banner.set('invisible', 'not %s' % DYNAMIC_FIELD_NAME)
        banner.text = 'Waiting Approval'

        arch = etree.tostring(data, encoding='unicode')

        if self.generated_view_id:
            self.generated_view_id.write({'arch_db': arch, 'active': True})
        else:
            self.generated_view_id = Views.create({
                'name': 'Dynamic Approval - %s' % self.name,
                'model': self.model_name,
                'inherit_id': base_view.id,
                'arch': arch,
                'type': 'form',
                'priority': 99,
            })


    # add this field near the other Text fields (approved_action / refused_action)
    description_template = fields.Html(
        string='Description Template',
        help=(
            "Default message shown in the Description box when someone clicks "
            "'Request Approval'. You can use placeholders like {record.display_name}, "
            "{user.name} — they will be replaced automatically with the real values."
        ),
    )

    def _render_description(self, record=False):
        """Fill in the Description Template with the real record's values.
        {record.display_name} is swapped for a clickable link to the record
        instead of plain text. Falls back to a generic message if no template
        is set, and never raises — a bad placeholder just returns the raw
        template text.

        record=False is valid — Approval Types with no Model configured
        (Create Request button, no target document) have nothing to link
        to, so {record.xxx} placeholders just resolve to empty text
        instead of crashing.
        """
        self.ensure_one()
        template = self.description_template

        # Build a clickable link (e.g. <a href="/odoo/sale.order/24">S00024</a>)
        # only when there IS a target record.
        record_link = record._get_html_link() if record else ''

        # Small wrapper so {record.display_name} in the template resolves to
        # the link instead of the plain name, while other {record.xxx} usages
        # (if any) still fall through to the real record when one exists.
        class _RecordProxy:
            def __init__(self, rec, link):
                self._rec = rec
                self.display_name = link

            def __getattr__(self, name):
                if self._rec:
                    return getattr(self._rec, name)
                return ''

        proxy = _RecordProxy(record, record_link)

        if not template:
            if record:
                return _(
                    'Hi,<br/>Please review my request.<br/>'
                    'Click on %s to view more!<br/>Thanks,'
                ) % (record_link,)
            return _('Hi,<br/>Please review my request.<br/>Thanks,')

        try:
            return template.format(record=proxy, user=self.env.user, type=self)
        except Exception:
            return template

    FIELD_OPTIONS = [
        ('required', 'Required'),
        ('optional', 'Optional'),
        ('none', 'None'),
    ]

    document_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Document Opt",
        default='none',
       
    )

    contact_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Contact Opt",
        default='none',
       
    )

    date_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Date Opt",
        default='none',
       
    )

    period_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Period Opt",
        default='none',
        
    )

    item_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Item Opt",
        default='none',
        
    )

    multi_items_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Multi Items Opt",
        default='none',
        
    )

    quantity_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Quantity Opt",
        default='none',
        
    )

    amount_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Amount Opt",
        default='none',
        
    )

    payment_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Payment Opt",
        default='none',
       
    )

    reference_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Reference Opt",
        default='none',
        
    )

    location_opt = fields.Selection(
        FIELD_OPTIONS,
        string="Location Opt",
        default='none',
        
    )