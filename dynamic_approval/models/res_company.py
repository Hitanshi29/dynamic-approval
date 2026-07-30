from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    minimum_amount = fields.Integer(string="Minimum Amount")
    set_amount = fields.Boolean(string="Set Amount")