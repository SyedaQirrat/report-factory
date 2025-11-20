# -*- coding: utf-8 -*-
from odoo import models, fields, api

class InventoryReportWizard(models.TransientModel):
    _name = 'mulphico.inventory.report.wizard'
    _description = 'Inventory Valuation Report Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    
    warehouse_ids = fields.Many2many(
        'stock.warehouse', string='Warehouses', required=True)
    
    location_ids = fields.Many2many(
        'stock.location', string='Locations', required=True,
        domain="[('usage', '=', 'internal'), ('warehouse_id', 'in', warehouse_ids)]")
    
    category_ids = fields.Many2many(
        'product.category', string='Product Categories', required=True)
    
    product_ids = fields.Many2many(
        'product.product', string='Products', required=True,
        domain="[('categ_id', 'in', category_ids)]")

    # This onchange automatically updates the locations when warehouses change
    @api.onchange('warehouse_ids')
    def _onchange_warehouse_ids(self):
        if self.warehouse_ids:
            return {'domain': {'location_ids': [
                ('usage', '=', 'internal'),
                ('warehouse_id', 'in', self.warehouse_ids.ids)
            ]}}
        else:
            return {'domain': {'location_ids': [('usage', '=', 'internal')]}}

    # This onchange automatically updates the products when categories change
    @api.onchange('category_ids')
    def _onchange_category_ids(self):
        if self.category_ids:
            return {'domain': {'product_ids': [
                ('categ_id', 'in', self.category_ids.ids)
            ]}}
        else:
            return {'domain': {'product_ids': []}}

    def action_print_report(self):
        """
        This is the button method.
        It returns an action that tells Odoo to render our QWeb report.
        """
        self.ensure_one()
        # Collect all the data from the wizard
        data = {
            'form': self.read()[0],
        }
        
        # Return the report action by its XML ID
        # The XML ID is <module_name>.<report_id>
        return self.env.ref('mulphico_inventory_report.action_report_inventory_valuation').report_action(self, data=data)