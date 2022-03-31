# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning

class ProductTemplate(models.Model) :
    _inherit = 'product.template'
    
    planner_spots = fields.Integer(string='Cupos', default=1)

class Product(models.Model) :
    _inherit = 'product.product'
    
    planner_spots = fields.Integer(string='Cupos', related='product_tmpl_id.planner_spots', store=True, readonly=False)