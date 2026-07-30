from odoo import models, fields
import logging
logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    minimum_amount = fields.Integer(string="Minimum Amount Of Orders",related="company_id.minimum_amount",readonly=False)
    set_amount = fields.Boolean(string="Set Amount",related="company_id.set_amount",readonly=False)