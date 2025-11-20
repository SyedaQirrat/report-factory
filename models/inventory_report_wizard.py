# -*- coding: utf-8 -*-
import base64
import io
from odoo import models, fields, api
from odoo.tools.misc import xlsxwriter

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

    # Fields to store the generated excel file
    excel_file = fields.Binary('Excel Report')
    excel_filename = fields.Char('Excel Filename', size=64)

    @api.onchange('warehouse_ids')
    def _onchange_warehouse_ids(self):
        if self.warehouse_ids:
            return {'domain': {'location_ids': [
                ('usage', '=', 'internal'),
                ('warehouse_id', 'in', self.warehouse_ids.ids)
            ]}}
        else:
            return {'domain': {'location_ids': [('usage', '=', 'internal')]}}

    @api.onchange('category_ids')
    def _onchange_category_ids(self):
        if self.category_ids:
            return {'domain': {'product_ids': [
                ('categ_id', 'in', self.category_ids.ids)
            ]}}
        else:
            return {'domain': {'product_ids': []}}

    def action_print_report(self):
        self.ensure_one()
        data = {'form': self.read()[0]}
        return self.env.ref('mulphico_inventory_report.action_report_inventory_valuation').report_action(self, data=data)

    def action_print_excel(self):
        self.ensure_one()
        
        # 1. Fetch Data using the existing Report Model Logic
        report_model = self.env['report.mulphico_inventory_report.report_inventory_valuation_template']
        data = {'form': self.read()[0]}
        # We manually call _get_report_values to get the calculated dictionary
        values = report_model._get_report_values(docids=[self.id], data=data)
        lines = values.get('report_lines', [])

        # 2. Setup Excel Workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Inventory Valuation')

        # 3. Formats
        header_format = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'font_size': 10
        })
        sub_header_format = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#F0F0F0', 'font_size': 9
        })
        cell_format = workbook.add_format({'border': 1, 'font_size': 9})
        num_format = workbook.add_format({'border': 1, 'font_size': 9, 'num_format': '#,##0.00'})

        # 4. Write Headers
        # Main Headers (Row 1)
        main_headers = [
            'Principal', 'Type', 'Model', 'Product Barcode', 'Product', 'Product Model', 'Product Category', 'Rate', 'Product Costing Method',
            'Opening', 'Receipts', 'Manufactured', 'Delivered', 'Adjustment', 'Scrap', 'Closing'
        ]
        
        # Columns 0-8 are single columns. Columns 9-15 (Opening to Closing) span 3 columns each.
        col_idx = 0
        for header in main_headers:
            if header in ['Opening', 'Receipts', 'Manufactured', 'Delivered', 'Adjustment', 'Scrap', 'Closing']:
                sheet.merge_range(0, col_idx, 0, col_idx + 2, header, header_format)
                col_idx += 3
            else:
                sheet.merge_range(0, col_idx, 1, col_idx, header, header_format)
                col_idx += 1

        # Sub Headers (Row 2) - Only for the quantitative columns
        # The first 9 columns are merged vertically, so we start writing sub-headers at column 9
        start_col = 9
        sections = ['Opening', 'Receipts', 'Manufactured', 'Delivered', 'Adjustment', 'Scrap', 'Closing']
        for _ in sections:
            sheet.write(1, start_col, 'QTY', sub_header_format)
            sheet.write(1, start_col + 1, 'Rate', sub_header_format)
            sheet.write(1, start_col + 2, 'Value', sub_header_format)
            start_col += 3

        # 5. Write Data Rows
        row = 2
        for line in lines:
            c = 0
            # Metadata Columns
            sheet.write(row, c, line.get('principal', ''), cell_format); c+=1
            sheet.write(row, c, line.get('type', ''), cell_format); c+=1
            sheet.write(row, c, line.get('product_model', ''), cell_format); c+=1 # Model column
            sheet.write(row, c, line.get('product_barcode', ''), cell_format); c+=1
            sheet.write(row, c, line.get('product_name', ''), cell_format); c+=1
            sheet.write(row, c, line.get('product_model', ''), cell_format); c+=1 # Product Model column (Placeholder used product.name)
            sheet.write(row, c, line.get('product_category', ''), cell_format); c+=1
            sheet.write(row, c, line.get('closing_rate', 0.0), num_format); c+=1 # Rate (usually closing rate or standard price)
            sheet.write(row, c, line.get('costing_method', ''), cell_format); c+=1

            # Value Columns
            groups = ['opening', 'receipt', 'manufactured', 'delivered', 'adjustment', 'scrap', 'closing']
            for group in groups:
                sheet.write(row, c, line.get(f'{group}_qty', 0.0), num_format); c+=1
                sheet.write(row, c, line.get(f'{group}_rate', 0.0), num_format); c+=1
                sheet.write(row, c, line.get(f'{group}_value', 0.0), num_format); c+=1
            
            row += 1

        workbook.close()
        output.seek(0)

        # 6. Save and Return Action
        filename = 'Inventory Valuation Report.xlsx'
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': filename
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=mulphico.inventory.report.wizard&id={}&field=excel_file&filename_field=excel_filename&download=true'.format(self.id),
            'target': 'self',
        }