# -*- coding: utf-8 -*-
from odoo import models, fields, api

class InventoryValuationReport(models.AbstractModel):
    _name = 'report.mulphico_inventory_report.report_inventory_valuation_template'
    _description = 'Inventory Valuation Report Data Model'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form'):
            return {}

        wizard_data = data['form']
        
        StockMoveLine = self.env['stock.move.line']
        ValuationLayer = self.env['stock.valuation.layer']

        date_from = wizard_data['date_from']
        date_to = wizard_data['date_to']
        location_ids = self.env['stock.location'].browse(wizard_data['location_ids'])
        product_ids = self.env['product.product'].browse(wizard_data['product_ids'])
        
        # Get warehouse names for the report header
        warehouse_objs = self.env['stock.warehouse'].browse(wizard_data['warehouse_ids'])
        warehouse_names = ', '.join(warehouse_objs.mapped('name'))

        report_lines = []

        for product in product_ids:
            # --- 1. Fetch Custom/Static Fields ---
            # NOTE: Ensure x_principal and x_device_type exist on product.product or product.template
            # Using getattr to prevent crash if fields are missing in DB
            principal = getattr(product, 'x_principal', 'N/A')
            device_type = getattr(product, 'x_device_type', 'N/A')
            
            # Costing Method is usually on the Category
            costing_method = product.categ_id.property_cost_method or 'standard'

            # PLACEHOLDER: Using product name as 'Product Model' as requested
            product_model_placeholder = product.name 

            # --- 2. Get Opening Balance ---
            opening_context = {'to_date': date_from, 'location': location_ids.ids}
            product_at_start = product.sudo().with_context(opening_context)
            
            opening_qty = product_at_start.qty_available
            opening_value = product_at_start.value_svl
            opening_rate = opening_value / opening_qty if opening_qty else 0.0

            # --- 3. Get Movements ---
            move_domain = [
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                '|',
                ('location_id', 'in', location_ids.ids),
                ('location_dest_id', 'in', location_ids.ids)
            ]
            move_lines = StockMoveLine.sudo().search(move_domain, order='date asc')
            
            receipt_qty, receipt_value = 0.0, 0.0
            manufactured_qty, manufactured_value = 0.0, 0.0
            delivered_qty, delivered_value = 0.0, 0.0
            adjustment_qty, adjustment_value = 0.0, 0.0
            scrap_qty, scrap_value = 0.0, 0.0

            for line in move_lines:
                # Calculate value for this specific move
                # Note: This sums all layers for the move. 
                line_val_layers = ValuationLayer.sudo().search([('stock_move_id', '=', line.move_id.id)])
                line_value = abs(sum(line_val_layers.mapped('value')))

                # IN moves (Destination is in selected locations)
                if line.location_dest_id.id in location_ids.ids and line.location_id.id not in location_ids.ids:
                    if line.move_id.picking_id and line.move_id.picking_id.picking_type_code == 'incoming':
                        receipt_qty += line.qty_done
                        receipt_value += line_value
                    elif line.move_id.production_id:
                        manufactured_qty += line.qty_done
                        manufactured_value += line_value
                    else:
                        # Treat others (like inventory adjustments) as adjustments
                        adjustment_qty += line.qty_done
                        adjustment_value += line_value

                # OUT moves (Source is in selected locations)
                elif line.location_id.id in location_ids.ids and line.location_dest_id.id not in location_ids.ids:
                    if line.move_id.picking_id and line.move_id.picking_id.picking_type_code == 'outgoing':
                        delivered_qty += line.qty_done
                        delivered_value += line_value
                    elif line.move_id.scrap_id:
                        scrap_qty += line.qty_done
                        scrap_value += line_value
                    else:
                        # Treat others as adjustments (negative quantity for OUT)
                        adjustment_qty -= line.qty_done
                        adjustment_value -= line_value

            # --- 4. Calculate Closing Balance ---
            closing_context = {'to_date': date_to, 'location': location_ids.ids}
            product_at_end = product.sudo().with_context(closing_context)
            
            closing_qty = product_at_end.qty_available
            closing_value = product_at_end.value_svl
            closing_rate = closing_value / closing_qty if closing_qty else 0.0

            # --- 5. Store Data ---
            report_lines.append({
                'principal': principal,
                'type': device_type,
                'product_barcode': product.barcode or '',
                'product_name': product.name or '',
                'product_model': product_model_placeholder, 
                'product_category': product.categ_id.display_name or '',
                'costing_method': costing_method,
                
                'opening_qty': opening_qty, 
                'opening_rate': opening_rate, 
                'opening_value': opening_value,
                
                'receipt_qty': receipt_qty, 
                'receipt_rate': receipt_value / receipt_qty if receipt_qty else 0.0, 
                'receipt_value': receipt_value,
                
                'manufactured_qty': manufactured_qty, 
                'manufactured_rate': manufactured_value / manufactured_qty if manufactured_qty else 0.0, 
                'manufactured_value': manufactured_value,
                
                'delivered_qty': delivered_qty, 
                'delivered_rate': delivered_value / delivered_qty if delivered_qty else 0.0, 
                'delivered_value': delivered_value,
                
                'adjustment_qty': adjustment_qty, 
                'adjustment_rate': adjustment_value / adjustment_qty if adjustment_qty else 0.0, 
                'adjustment_value': adjustment_value,
                
                'scrap_qty': scrap_qty, 
                'scrap_rate': scrap_value / scrap_qty if scrap_qty else 0.0, 
                'scrap_value': scrap_value,
                
                'closing_qty': closing_qty, 
                'closing_rate': closing_rate, 
                'closing_value': closing_value,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'mulphico.inventory.report.wizard',
            'data': data,
            'report_lines': report_lines,
            'date_from': date_from,
            'date_to': date_to,
            'warehouse_names': warehouse_names,
        }