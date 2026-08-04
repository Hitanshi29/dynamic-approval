from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree   
from markupsafe import Markup


DYNAMIC_FIELD_NAME = 'x_dynamic_approval_pending'


class MultiApprovalType(models.Model):
    _name = 'multi.approval.type'
    _description = 'Approval Type'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Char(string="Description", tracking=True)
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
        ondelete='cascade',tracking=True
    )
    model_name = fields.Char(
        string='Model Name', related='model_id.model', store=True, readonly=True,
    )

    @api.constrains('model_id', 'is_model')
    def _check_unique_model(self):
        """A given Model can only be linked to ONE Approval Type."""
        for rec in self:
            if rec.is_model and rec.model_id:
                duplicate = self.search([
                    ('id', '!=', rec.id),
                    ('is_model', '=', True),
                    ('model_id', '=', rec.model_id.id),
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        'An Approval Type ("%s") is already configured for the '
                        'model "%s". Only one Approval Type is allowed per Model.'
                    ) % (duplicate.name, rec.model_id.name))


    approver_ids = fields.One2many(
        'multi.approval.type.line', 'approval_type_id', string='Approvers'
    )

    domain = fields.Char(
        string='Domain', default='[]',
        help='Filter used to match records this rule applies to.',tracking=True
    )

    hide_buttons_from_model_view = fields.Boolean(
        string='Hide Buttons from Model View?',default=True,
        help='If checked, the record\'s own workflow buttons are hidden while approval is pending.'
    )

    approved_action = fields.Text(
        string='Approved Action',
        help='Python executed on the record when approved. Use "record" for the document.',
        tracking=True
    )
    refused_action = fields.Text(
        string='Cancel Action',
        help='Python executed on the record when refused. Use "record" for the document.',
        tracking=True
    )

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
                'default_record_amount': 0.0,
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
            'ttype': 'char', 
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
        """Convert an Odoo domain into a JS/view expression.

        Supports:
        &, |, !
        =, !=, >, <, >=, <=, in, not in
        """
        import ast

        try:
            domain = ast.literal_eval(domain_str or "[]")
        except Exception:
            return [], "True"

        if not domain:
            return [], "True"

        fields_used = set()

        op_map = { "=": "==","!=": "!=",">": ">","<": "<",">=": ">=","<=": "<=","in": "in","not in": "not in",}

        def leaf_to_expr(leaf):
            field, operator, value = leaf
            fields_used.add(field)

            if operator not in op_map:
                return "True"

            return "%s %s %r" % (field, op_map[operator], value)

        def parse(tokens):
            token = tokens.pop(0)

            if token == "&":
                left = parse(tokens)
                right = parse(tokens)
                return "(%s) and (%s)" % (left, right)

            elif token == "|":
                left = parse(tokens)
                right = parse(tokens)
                return "(%s) or (%s)" % (left, right)

            elif token == "!":
                expr = parse(tokens)
                return "not (%s)" % expr

            elif isinstance(token, (tuple, list)) and len(token) == 3:
                return leaf_to_expr(token)

            return "True"

        tokens = list(domain)

        if tokens and tokens[0] in ("&", "|", "!"):
            expr = parse(tokens)
        else:
            # Flat AND domain
            expr = " and ".join(
                leaf_to_expr(x)
                for x in tokens
                if isinstance(x, (tuple, list))
            )

        return list(fields_used), expr


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

        req_btn = etree.SubElement(header_xpath, 'button')
        req_btn.set('name', 'action_request_approval_dynamic')
        req_btn.set('type', 'object')
        req_btn.set('string', 'Request Approval')
        req_btn.set('class', 'oe_highlight')
        req_btn.set('invisible', "%s in ('submitted', 'approved', 'rejected', 'resolved') or not (%s)" % (DYNAMIC_FIELD_NAME, eligible_expr))
        req_btn.set('context', "{'approval_type_id': %d}" % self.id)

        view_btn = etree.SubElement(header_xpath, 'button')
        view_btn.set('name', view_name)
        view_btn.set('type', 'action')
        view_btn.set('string', 'View Approval')
        view_btn.set('invisible', "%s not in ('submitted', 'rejected')" % DYNAMIC_FIELD_NAME)

        reset_btn = etree.SubElement(header_xpath, 'button')
        reset_btn.set('name', 'action_reset_dynamic_approval')
        reset_btn.set('type', 'object')
        reset_btn.set('string', 'Request Again')
        reset_btn.set('class', 'btn-secondary')
        reset_btn.set(
            'invisible',
            "%s != 'rejected'" % DYNAMIC_FIELD_NAME
        )

        if self.hide_buttons_from_model_view and eligible_expr != 'True':
           
            try:
                resolved = self.env[self.model_name].get_view(
                    view_id=base_view.id, view_type='form'
                )
                arch_root = etree.fromstring(resolved['arch'].encode())
            except Exception:
                arch_root = None

            header_node = arch_root.find('.//header') if arch_root is not None else None
            if header_node is not None:
                seen_positions = {} 
                for btn in header_node.findall('button'):
                    name = btn.get('name')
                    if not name or name in (req_name, view_name):
                        continue

                    seen_positions[name] = seen_positions.get(name, 0) + 1
                    occurrence = seen_positions[name]

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

                    combined = (
                        "(%s) or "
                        "((%s) and %s not in ('approved', 'resolved'))"
                    ) % (
                        existing_invisible,
                        eligible_expr,
                        DYNAMIC_FIELD_NAME,
                    )

                
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
                        attr2 = etree.SubElement(btn_xpath, 'attribute')
                        attr2.set('name', 'states')
                       
        sheet_xpath = etree.SubElement(data, 'xpath')
        sheet_xpath.set('expr', "//form/sheet")
        sheet_xpath.set('position', 'before')

        banner = etree.SubElement(sheet_xpath, 'div')
        banner.set('class', 'alert alert-info')
        banner.set('role', 'alert')
        banner.set('invisible', "%s != 'submitted'" % DYNAMIC_FIELD_NAME)
        banner.text = 'Waiting Approval'

        reject_xpath = etree.SubElement(data, 'xpath')
        reject_xpath.set('expr', "//form/sheet")
        reject_xpath.set('position', 'before')

        reject_banner = etree.SubElement(reject_xpath, 'div')
        reject_banner.set('class', 'alert alert-danger')
        reject_banner.set('role', 'alert')
        reject_banner.set('invisible',"%s != 'rejected'" % DYNAMIC_FIELD_NAME)
        reject_banner.text = (
            "Approval was rejected. Please modify this document and request approval again."
        )

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


    description_template = fields.Html(
        string='Description Template',
        default=lambda self: _(
            'Hi,<br/>Please review my request.<br/>'
            'Click {record.display_name} to view more!<br/>Thanks,'
        ),
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
        """
        self.ensure_one()
        template = self.description_template

        if record:
            url = '/web#model=%s&view_type=form&id=%s' % (record._name, record.id)
            record_link = Markup('<a href="%s" target="_blank">%s</a>') % (url, record.display_name)
        else:
            record_link = ''

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
                result = _(
                    'Hi,<br/>Please review my request.<br/>'
                    'Click on %s to view more!<br/>Thanks,'
                ) % (record_link,)
            else:
                result = _('Hi,<br/>Please review my request.<br/>Thanks,')
            return Markup(result)

        try:
            result = template.format(record=proxy, user=self.env.user, type=self)
        except Exception:
            result = template

        return result if isinstance(result, Markup) else Markup(result)
        

    FIELD_OPTIONS = [
        ('required', 'Required'),
        ('optional', 'Optional'),
        ('none', 'None'),
    ]

    document_opt = fields.Selection(FIELD_OPTIONS,string="Document Opt", default='none',)

    contact_opt = fields.Selection(FIELD_OPTIONS,string="Contact Opt",default='none',)

    date_opt = fields.Selection(FIELD_OPTIONS,string="Date Opt", default='none',)

    period_opt = fields.Selection(FIELD_OPTIONS,string="Period Opt", default='none',)

    item_opt = fields.Selection(FIELD_OPTIONS,string="Item Opt",default='none',)

    multi_items_opt = fields.Selection(FIELD_OPTIONS,string="Multi Items Opt",default='none',)

    quantity_opt = fields.Selection(FIELD_OPTIONS,string="Quantity Opt",default='none',)

    amount_opt = fields.Selection(FIELD_OPTIONS,string="Amount Opt",default='none',)

    payment_opt = fields.Selection(FIELD_OPTIONS,string="Payment Opt",default='none',)

    reference_opt = fields.Selection(FIELD_OPTIONS,string="Reference Opt",default='none',)

    location_opt = fields.Selection( FIELD_OPTIONS,string="Location Opt",default='none',)