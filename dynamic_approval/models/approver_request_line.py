from odoo import fields, models

class ApprovalRequestLine(models.Model):
    
    _name = 'approval.request.line'
    _description = 'Approval Request Step'
    _order = 'sequence, id'

    request_id = fields.Many2one(
        'approval.request', string='Request', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    title = fields.Char(string='Title')
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    minimum_amount = fields.Float(string='Minimum Amount')
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], string='Status', default='waiting')
    approved_date = fields.Datetime(string='Approved On')



class ApprovalRequestItemLine(models.Model):
    _name = 'approval.request.item.line'
    _description = 'Approval Request Item Line'

    request_id = fields.Many2one(
        'approval.request', string='Request', required=True, ondelete='cascade')
    name = fields.Char(string='Item', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    amount = fields.Float(string='Amount')

    # Using product module
    
    # request_id = fields.Many2one(
    #         'approval.request', string='Request', required=True, ondelete='cascade')
    # product_id = fields.Many2one('product.product', string='Product')
    # name = fields.Char(string='Item', required=True)
    # quantity = fields.Float(string='Quantity', default=1.0)
    # amount = fields.Float(string='Amount')

    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     for rec in self:
    #         if rec.product_id:
    #             rec.name = rec.product_id.display_name
    #             rec.amount = rec.product_id.list_price