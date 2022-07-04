# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class stock_quant(models.Model):
	_inherit = 'stock.quant'

	force_date = fields.Datetime(string="Force Date")

	def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
		res = super(stock_quant, self)._get_inventory_move_values(qty, location_id, location_dest_id, out=out)
		if self.env.user.has_group('stock_force_date_app.group_stock_force_date') and self.force_date:
			res.update({'date':self.force_date,'date_deadline':self.force_date})
		return res

	@api.model
	def _get_inventory_fields_write(self):
		""" Returns a list of fields user can edit when editing a quant in `inventory_mode`."""
		res = super(stock_quant, self)._get_inventory_fields_write()
		res += ['force_date']
		return res

	# @api.model
	# def _get_inventory_fields_create(self):
	# 	""" Returns a list of fields user can edit when editing a quant in `inventory_mode`."""
	# 	res = super(stock_quant, self)._get_inventory_fields_create()
	# 	res += ['force_date']
	# 	return res

	@api.model
	def create(self, vals):
		force_date = vals.get('force_date')
		res = super(stock_quant, self).create(vals)
		if self.env.context.get('import_file') and force_date:
			for line in res:
				line.write({'force_date':force_date})
		return res


class StockPicking(models.Model):
	_inherit = 'stock.picking'

	force_date = fields.Datetime(string="Force Date")


class StockMove(models.Model):
	_inherit = 'stock.move'

	def _action_done(self, cancel_backorder=False):
		force_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
		if self.env.user.has_group('stock_force_date_app.group_stock_force_date'):
			for move in self:
				force_date = move.date
				if move.picking_id:
					if move.picking_id.force_date:
						force_date = move.picking_id.force_date
					else:
						force_date = move.picking_id.scheduled_date

		res = super(StockMove, self)._action_done()
		if self.env.user.has_group('stock_force_date_app.group_stock_force_date'):
			if force_date:
				for move in res:
					move.write({'date':force_date,'date_deadline':force_date})
					for valuation_layer in move.stock_valuation_layer_ids:
						date = move.date_deadline or move.date
						self.env.cr.execute("update stock_valuation_layer set create_date = %s where id = %s", (date, valuation_layer.id))
					if move.move_line_ids:
						for move_line in move.move_line_ids:
							move_line.write({'date':force_date})
					if move.account_move_ids:
						for account_move in move.account_move_ids:
							account_move.write({'date':force_date})
							# if move.inventory_id:
							# 	account_move.write({'ref':move.inventory_id.name})

		return res
