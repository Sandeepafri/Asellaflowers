# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright 2019 EquickERP
#
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import base64
import xlrd
import binascii
import tempfile


class wizard_transfer(models.TransientModel):
    _name = 'wizard.transfer'
    _description = "Wizard Transfer"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)
    name = fields.Char(string='File Name', readonly=True)
    data = fields.Binary(string='File')
    inward_operation_type_id = fields.Many2one('stock.picking.type', string='Inward Operation Type')
    outward_operation_type_id = fields.Many2one('stock.picking.type', string='Outward Operation Type')

    def import_transfer_record(self):
        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.data))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        product_product_obj = self.env['product.product']
        transfer_obj = self.env['stock.picking']
        inward_transfer_obj = self.env['stock.picking']
        outward_transfer_obj = self.env['stock.picking']

        customer_location_id, vendor_location_id = self.env['stock.warehouse']._get_partner_locations()

        for sheet in workbook.sheets():
            keys = sheet.row_values(0)
            xls_reader = [sheet.row_values(i) for i in range(1, (sheet.nrows))]
            sale_order_id = False
            for row in xls_reader:
                product_id = product_product_obj.search([('name', '=', row[3])],limit=1)
                if not product_id:
                    product_id = product_product_obj.create({'name':row[3],'type':'product'})
                
                if not product_id:
                    continue
                if not row[0]:
                    continue

                source_document = row[0].strip()
                date = fields.Datetime.now()
                qty = row[4]
                unit_price = row[5]
                analytic_account_name = row[6].strip()

                analytic_account_id = False

                if analytic_account_name:
                    analytic_account_id = self.env['account.analytic.account'].search([('name','=',analytic_account_name),('company_id','=',self.company_id.id)],limit=1)
                    if not analytic_account_id:
                        analytic_account_id = self.env['account.analytic.account'].create({'name':analytic_account_name,'company_id':self.company_id.id})

                if source_document.startswith('GRN'):
                    picking_type_id = self.inward_operation_type_id
                    source_location_id = vendor_location_id
                    location_dest_id = self.inward_operation_type_id.default_location_dest_id
                else:
                    picking_type_id = self.outward_operation_type_id
                    location_dest_id = customer_location_id
                    source_location_id = self.outward_operation_type_id.default_location_src_id

                if row[1]:
                    date = datetime.strptime(row[1], '%d-%m-%Y')

                picking_id = transfer_obj.search([('origin','=',source_document),('state','not in',('done','cancel')),('picking_type_id','=',picking_type_id.id)],limit=1)
                if not picking_id:
                    vals = {'picking_type_id': picking_type_id.id,'date': date,
                        'origin': source_document,'company_id': self.company_id.id,
                        'location_dest_id':location_dest_id.id,
                        'date_done': date,
                        'location_id': source_location_id.id
                        }
                    picking_id = transfer_obj.create(vals)
                move_id = self.env['stock.move'].create(self.prepare_stock_move_vals(picking_id,product_id,unit_price,qty,analytic_account_id))

    def prepare_stock_move_vals(self,picking_id,product_id,unit_price,qty,analytic_account_id):
        product = product_id
        description_picking = product._get_description(picking_id.picking_type_id)
        date_planned = picking_id.date
        return {
            'name': (picking_id.name or '')[:2000],
            'product_id': product_id.id,
            'date': date_planned,
            'date_deadline': date_planned,
            'location_id': picking_id.location_id.id,
            'location_dest_id': picking_id.location_dest_id.id,
            'picking_id': picking_id.id,
            'state': 'draft',
            'company_id': self.company_id.id,
            'price_unit': unit_price,
            'picking_type_id': picking_id.picking_type_id.id,
            'origin': picking_id.origin,
            'description_picking': description_picking,
            'warehouse_id': picking_id.picking_type_id.warehouse_id.id,
            'product_uom_qty': qty,
            'analytic_account_id':analytic_account_id.id if analytic_account_id else False,
            'product_uom': product_id.uom_id.id,
        }

class stock_valuation_layer(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(stock_valuation_layer, self).create(vals_list)
        for each_rec in res:
            if each_rec.stock_move_id:
                date = each_rec.stock_move_id.date_deadline or each_rec.stock_move_id.date
                self.env.cr.execute("update stock_valuation_layer set create_date = %s where id = %s", (date, each_rec.id))
        return res

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super(stock_picking, self)._action_done()
        for picking in self:
            picking.write({'date_done':picking.scheduled_date})
        return res

    def transfer_draft_to_ready(self):
        for picking in self.filtered(lambda l:l.state not in ('done','cancel')):
            picking.action_confirm()
            picking.action_assign()

# class stock_move(models.Model):
#     _inherit = 'stock.move'

#     def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
#         self.ensure_one()
#         AccountMove = self.env['account.move'].with_context(default_journal_id=journal_id)

#         move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
#         if move_lines:
#             if self.date_deadline:
#                 date = self.date_deadline
#             else:
#                 date = self._context.get('force_period_date', fields.Date.context_today(self))
#             new_account_move = AccountMove.sudo().create({
#                 'journal_id': journal_id,
#                 'line_ids': move_lines,
#                 'date': date,
#                 'ref': description,
#                 'stock_move_id': self.id,
#                 'stock_valuation_layer_ids': [(6, None, [svl_id])],
#                 'move_type': 'entry',
#             })
#             new_account_move._post()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
