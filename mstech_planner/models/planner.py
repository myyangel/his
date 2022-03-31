# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
#from odoo.tools.misc import format_date, format_datetime
import datetime
import pytz

DEFAULT_TIMEZONE = 'America/Lima'

#def local_datetime(untimed_datetime, timezone) :
#    return untimed_datetime.astimezone(pytz.timezone(timezone))

class PlannerProfessional(models.Model) :
    _name = 'planner.professional'
    _description = 'Professional'
    #_rec_name = 'employee_id'
    #_check_company_auto = True
    
    @api.model
    def _get_default_company_id(self) :
        company_id = self.env.company
        return company_id
    
    #company_id = fields.Many2one(comodel_name='res.company', string='Compañía', default=_get_default_company_id)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    procedure_ids = fields.Many2many(comodel_name='product.product', string='Procedures', domain=[('type','=','service')])
    
    @api.depends('employee_id')
    def name_get(self) :
        #result = []
        #for record in self :
        #    result.append((record.id, record.employee_id.display_name))
        result = [(record.id, record.employee_id.display_name) for record in self]
        return result

class PlannerSpot(models.Model) :
    _name = 'planner.spot'
    _description = 'Spot'
    _order = 'professional_id asc, start asc, end asc'
    #_check_company_auto = True
    
    def _get_default_timezone(self) :
        #datetime.datetime.now(pytz.timezone('America/Lima')).utcoffset()
        return DEFAULT_TIMEZONE
    
    @api.model
    def _get_default_company_id(self) :
        company_id = self.env.company
        return company_id
    
    name = fields.Char(string='Planner', readonly=True, copy=False, compute='_compute_name', store=True)
    active = fields.Boolean(string='Active', default=True)
    #company_id = fields.Many2one(comodel_name='res.company', string='Compañía', default=_get_default_company_id)
    professional_id = fields.Many2one(comodel_name='planner.professional', string='Professional')
    date = fields.Date(string='Date', compute='_compute_date', store=True, readonly=True)
    start = fields.Datetime(string='Start', required=True)
    end = fields.Datetime(string='End', required=True)
    spots = fields.Integer(string='Spots', default=1, required=True)
    #planner_ids = fields.One2many(comodel_name='planner.planner', inverse_name='spot_id', string='Planners', domain=[('state','!=','cancel')])
    planner_ids = fields.Many2many(comodel_name='planner.planner', relation='planner_spot_planner_planner_table_1', column1='spot_id', column2='planner_id', string='Planners')
    available_spots = fields.Integer(string='Available Spots', compute='_compute_available_spots', store=True, readonly=False)
    
    sql_constraints = [
        ('start_end_check', 'CHECK((start < end))', 'La hora de inicio debe ser anterior a la hora de fin.'),
        ('professional_start_unique', 'UNIQUE(professional_id, start)', 'Un profesional solo puede tener un cupo que empiece a esta hora.'),
    ]
    
    @api.depends('start')
    def _compute_date(self) :
        for record in self :
            start = record.start
            record.date = start and fields.Datetime.context_timestamp(self, start).date()
    
    @api.depends('spots', 'planner_ids', 'planner_ids.spots')
    def _compute_available_spots(self) :
        for record in self :
            #available_spots = record.spots - len(record.planner_ids)
            available_spots = record.planner_ids.planner_spot_ids_condition().mapped('spots')
            available_spots = record.spots - sum(available_spots or [0])
            #if available_spots < 0 :
            #    raise UserError('Error')
            record.available_spots = max(available_spots, 0)
    
    def get_name_tuple(self) :
        self.ensure_one()
        current_tz = self.env.user.tz or self._get_default_timezone()
        current_offset = datetime.datetime.now(pytz.timezone(current_tz)).utcoffset()
        start = self.start + current_offset
        name = (
            self.professional_id.display_name,
            start.strftime('%d/%m/%Y'), #format_date(self.env, spot.date, date_format='dd/MM/Y'),
            start.strftime('%H:%M:%S'), #format_datetime(self.env, spot.start, tz=current_tz, dt_format='HH:mm:ss'),
            (self.end + current_offset).strftime('%H:%M:%S'), #format_datetime(self.env, spot.end, tz=current_tz, dt_format='HH:mm:ss'),
        )
        return name
    
    def get_name(self) :
        self.ensure_one()
        name = '/'
        if self.professional_id and self.date and self.start and self.end :
            name = self.get_name_tuple()
            name = ('%s: %s %s - %s') % name
        return name
    
    @api.depends('professional_id', 'start', 'end')
    def name_get(self) :
        result = []
        for spot in self :
            name = spot.get_name()
            result.append((spot.id, name))
        return result
    
    @api.depends('professional_id', 'start', 'end')
    def _compute_name(self) :
        names = dict(self.name_get())
        for record in self :
            record.name = names.get(record.id)
    
    @api.model
    def spot_archival(self) :
        current_tz = self.env.user.tz or self._get_default_timezone()
        current_date = datetime.datetime.now(pytz.timezone(current_tz)).date()
        to_delete = self.env[self._name].sudo().search([('available_spots','>',0), ('date','<',str(current_date))])
        for record in to_delete :
            record.spots = record.spots - record.available_spots

class PlannerProfessionalAvailability(models.Model) :
    _name = 'planner.professional.availability'
    _description = 'Availability'
    _order = 'professional_id asc, day asc'
    #_check_company_auto = True
    
    def _get_default_timezone(self) :
        return DEFAULT_TIMEZONE
    
    @api.model
    def _get_default_company_id(self) :
        company_id = self.env.company
        return company_id
    
    name = fields.Char(string='Availability', readonly=True, copy=False, compute='_compute_name', store=True, default='/')
    #company_id = fields.Many2one(comodel_name='res.company', string='Compañía', default=_get_default_company_id)
    professional_id = fields.Many2one(comodel_name='planner.professional', string='Professional', required=True)
    day = fields.Selection(selection=[('1','Monday'),('2','Tuesday'),('3','Wednesday'),('4','Thursday'),('5','Friday'),('6','Saturday'),('7','Sunday')],
                           string='Day', default='1', required=True)
    start = fields.Float(string='Start', default=8)
    end = fields.Float(string='End', default=18)
    duration = fields.Float(string='Duration', default=0.5, required=True)
    spots = fields.Integer(string='Spots', default=1, required=True)
    
    _sql_constraints = [
        ('unique_professional_id_day', 'UNIQUE(professional_id, day)', 'There can only be one availability for the professional on this day.'),
        ('start_end_check', 'CHECK((start < end))', 'La hora de inicio debe ser anterior a la hora de fin.')
    ]
    
    def get_name_tuple(self) :
        self.ensure_one()
        current_tz = self.env.user.tz or self._get_default_timezone()
        current_offset = datetime.datetime.now(pytz.timezone(current_tz)).utcoffset()
        start = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
        end = start + datetime.timedelta(hours=self.end) - current_offset
        start = start + datetime.timedelta(hours=self.start) - current_offset
        name = (
            self.professional_id.display_name,
            dict(self._fields['day'].selection)[self.day],
            (start + current_offset).strftime('%H:%M'), #format_datetime(self.env, start, tz=current_tz, dt_format='HH:mm'),
            (end + current_offset).strftime('%H:%M'), #format_datetime(self.env, end, tz=current_tz, dt_format='HH:mm'),
        )
        return name
    
    def get_name(self) :
        self.ensure_one()
        name = '/'
        if self.professional_id and self.day :
            name = self.get_name_tuple()
            name = ('%s: %s %s - %s') % name
        return name
    
    @api.depends('professional_id', 'day', 'start', 'end')
    def name_get(self) :
        result = []
        current_tz = self.env.user.tz or self._get_default_timezone()
        current_offset = datetime.datetime.now(pytz.timezone(current_tz)).utcoffset()
        for avail in self :
            name = avail.get_name()
            result.append((avail.id, name))
        return result
    
    @api.depends('professional_id', 'day', 'start', 'end')
    def _compute_name(self) :
        names = dict(self.name_get())
        for record in self :
            record.name = names.get(record.id)
    
    @api.model
    def spot_creation(self, availability_record=False, weeks_to_generate=5) :
        current_tz = self.env.user.tz or self._get_default_timezone()
        current_offset = datetime.datetime.now(pytz.timezone(current_tz)).utcoffset()
        aware_now = fields.Datetime.now().astimezone(pytz.timezone(current_tz))
        #aware_today = aware_now.date()
        spot = self.env['planner.spot'].sudo()
        for record in (availability_record or self.sudo().search([('day','=',str(aware_now.date().isoweekday()))])) :
            duration = record.duration
            duration_offset = datetime.timedelta(hours=duration)
            spots = record.spots
            aware_today = aware_now.date() + datetime.timedelta(days=int(record.day)-aware_now.date().isoweekday())
            for i in range(weeks_to_generate) :
                actual = aware_today + datetime.timedelta(weeks=i)
                if actual >= aware_now.date() :
                    start = record.start
                    end = record.end
                    unaware_starts = []
                    while start < end :
                        unaware_start = datetime.datetime.combine(actual, datetime.datetime.min.time())
                        unaware_start = unaware_start + datetime.timedelta(hours=start) - current_offset
                        unaware_starts.append(unaware_start)
                        start = start + duration
                        if start > end :
                            record.end = start
                    for unaware_start in unaware_starts :
                        spot_ids = spot.search([
                            ('professional_id','=',record.professional_id.id),
                            ('start','=',str(unaware_start)),
                            ('end','<=',str(unaware_start+duration_offset)),
                        ])
                        if not spot_ids.ids :
                            spot.create({
                                'professional_id': record.professional_id.id,
                                'date': str(actual),
                                'start': str(unaware_start),
                                'end': str(unaware_start + duration_offset),
                                'spots': spots,
                            })
                        else :
                            for spot_id in spot_ids :
                                if spot_id.spots != spots and spot_id.available_spot >= spot_id.spots - spots :
                                    spot_id.spots = spots
    
    @api.model
    def create(self, values) :
        if values.get('start') and values['start'] < 0 :
            values['start'] = 0
        if values.get('end') and values['end'] > 24 :
            values['end'] = 24
        res = super(PlannerProfessionalAvailability, self).create(values)
        self.spot_creation(availability_record=res)
        return res
    
    def write(self, values) :
        if values.get('start') and values['start'] < 0 :
            values['start'] = 0
        if values.get('end') and values['end'] > 24 :
            values['end'] = 24
        res = super(PlannerProfessionalAvailability, self).write(values)
        if values.get('spots') :
            spot = self.env['planner.spot'].sudo()
            for record in self :
                for spot_id in spot.search([('professional_id','=',record.professional_id.id)]) :
                    if spot_id.date.isoweekday() == int(record.day) and spot_id.available_spot >= spot_id.spots - values['spots'] :
                        spot_id.spots = values['spots']
        return res

#class SaleOrder(models.Model) :
#    _inherit = 'sale.order'
#    
#    planner_ids = fields.One2many(comodel_name='planner.planner', inverse_name='sale_id', string='Planner')
#    is_planner = fields.Boolean(string='Orden de Agenda')

class PlannerPlanner(models.Model) :
    _name = 'planner.planner'
    _description = 'Planner'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'patient_id asc, professional_id asc, start asc, end asc'
    #_check_company_auto = True
    
    def _get_default_timezone(self) :
        return DEFAULT_TIMEZONE
    
    @api.model
    def _get_default_company_id(self) :
        company_id = self.env.company
        return company_id
    
    name = fields.Char(string='Planner', readonly=True, copy=False, compute='_compute_name', store=True)
    #company_id = fields.Many2one(comodel_name='res.company', string='Compañía', default=_get_default_company_id)
    state = fields.Selection(string='Status', required=True, readonly=True, copy=False, tracking=True, default='planned',
                             selection=[('planned','Planned'),('received','Received'),('attended','Attended'),('cancel','Cancelled')])
    received = fields.Boolean(string='Received', compute='_compute_state', store=True, readonly=False)
    attended = fields.Boolean(string='Attended', compute='_compute_state', store=True)
    patient_id = fields.Many2one(comodel_name='res.partner', string='Patient', tracking=True, readonly=False, states={'cancel': [('readonly', True)]})
    professional_id = fields.Many2one(comodel_name='planner.professional', string='Professional', tracking=True)
    procedure_ids = fields.Many2many(comodel_name='product.product', string='Procedures', compute='_compute_professional_id', store=True, readonly=False)
    procedure_id = fields.Many2one(comodel_name='product.product', string='Procedure', tracking=True)
    has_available_spots = fields.Boolean(string='Disponible', compute='_compute_special_spots')
    available_spots = fields.Integer(string='Cupos Disponibles', compute='_compute_special_spots')
    spots = fields.Integer(string='Cupos', compute='_compute_special_spots')
    spots_from_line = fields.Boolean(string='Cupos desde Línea', default=False)
    spot_id = fields.Many2one(comodel_name='planner.spot', string='Spot', domain="[('professional_id','=',professional_id), '|', ('available_spots','>',0), ('id','in',spot_ids)]")
    spot_ids = fields.Many2many(comodel_name='planner.spot', relation='planner_spot_planner_planner_table_1', column1='planner_id', column2='spot_id', string='Cupos', compute='_compute_spot_ids', store=True, readonly=False)
    #spot_ids = fields.Many2many(comodel_name='planner.spot', relation='planner_spot_planner_planner_table_1', column1='planner_id', column2='spot_id', string='Cupos')
    date = fields.Date(string='Date', compute='_compute_date', store=True, readonly=True)
    #start = fields.Datetime(string='Start', compute='_compute_start_duration', store=True, readonly=False)
    #total_duration = fields.Float(string='Duración', compute='_compute_start_duration', store=True, readonly=False)
    start = fields.Datetime(string='Start', tracking=True)
    total_duration = fields.Float(string='Duración', tracking=True)
    end = fields.Datetime(string='End', compute='_compute_end', store=True, readonly=True)
    #sale_id = fields.Many2one(comodel_name='sale.order', string='Sale Order', tracking=True)
    line_ids = fields.One2many(comodel_name='planner.planner.line', inverse_name='planner_id', string='Líneas de Agenda')
    
    #def _prepare_sale_order_values(self) :
    #    self.ensure_one()
    #    values = {
    #        'partner_id': self.patient_id.id,
    #        'user_id': self.env.uid,
    #        'is_planner': True,
    #    }
    #    return values
    
    #def _create_sale_order(self) :
    #    for record in self :
    #        sale_order = record._prepare_sale_order_values()
    #        sale_order = self.env['sale.order'].sudo().create(sale_order)
    #        record.sale_id = sale_order
    #        sale_order.user_id = self.env.user
    #        for line in record.line_ids :
    #            sale_order_line = line._prepare_sale_order_line_values()
    #            sale_order.write({'order_line': [(0, 0, sale_order_line)]})
    #            sale_order_line = sale_order.order_line.filtered(lambda r: not r.planner_line_id)[0]
    #            line.sale_line_id = sale_order_line
    #            sale_order_line.planner_line_id = line
    
    #def create_sale_order(self) :
    #    to_order = self.filtered(lambda r: r.id and (not r.sale_id) and r.patient_id and len(r.line_ids))
    #    patients = to_order.mapped('patient_id')
    #    for patient in patients :
    #        records = to_order.filtered(lambda r: r.patient_id == patient)
    #        #sale_order = self.env['sale.order'].create({'partner_id': patient.id, 'user_id': self.env.uid})
    #        #records.write({'sale_id': sale_order.id})
    #        #for record in records :
    #        #    sale_order.write({'order_line': [(0,0,{'product_id': record.procedure_id.id})]})
    #        #    sale_order_line = sale_order.order_line.filtered(lambda r: not r.planner_id)[0]
    #        #    record.write({'sale_line_id': sale_order_line.id})
    #        #    sale_order_line.write({'planner_id': record.id})
    #        records._create_sale_order()
    
    def receive_patient(self) :
        #self.filtered(lambda r: r.state=='planned').write({'state': 'received'})
        for record in self :
            if record.state == 'planned' :
                record.state = 'received'
    
    def mark_attended(self) :
        #self.filtered(lambda r: r.state=='received').write({'state': 'attended'})
        for record in self :
            if record.state == 'received' :
                record.state = 'attended'
    
    def mark_cancel(self) :
        #self.filtered(lambda r: r.state not in ['attended','cancel']).write({'state': 'cancel'})
        for record in self.filtered(lambda r: r.state not in ['attended','cancel']) :
            if record.state not in ['attended','cancel'] :
                record.state = 'cancel'
    
    def get_name_tuple(self) :
        self.ensure_one()
        current_tz = self.env.user.tz or self._get_default_timezone()
        current_offset = datetime.datetime.now(pytz.timezone(current_tz)).utcoffset()
        start = self.start + current_offset
        name = (
            self.patient_id.name,
            self.professional_id.display_name,
            self.procedure_id.name,
            start.strftime('%d/%m/%Y'), #format_date(self.env, planner.date, date_format='dd/MM/Y'),
            start.strftime('%H:%M'), #format_datetime(self.env, planner.start, tz=current_tz, dt_format='HH:mm'),
            (start + datetime.timedelta(hours=self.total_duration)).strftime('%H:%M'), #format_datetime(self.env, planner.end, tz=current_tz, dt_format='HH:mm'),
        )
        return name
    
    def get_name(self) :
        self.ensure_one()
        name = '/'
        if self.patient_id and self.professional_id and self.start :
            name = self.get_name_tuple()
            name = _('Appointment from %s with %s for %s on the %s from %s to %s') % name
        return name
    
    @api.depends('patient_id', 'professional_id', 'start', 'total_duration')
    def name_get(self) :
        result = []
        for planner in self :
            name = planner.get_name()
            result.append((planner.id, name))
        return result
    
    @api.depends('patient_id', 'professional_id', 'start', 'total_duration')
    def _compute_name(self) :
        names = dict(self.name_get())
        for record in self :
            record.name = names.get(record.id)
    
    @api.depends('state')
    def _compute_state(self) :
        #self.filtered(lambda r: r.state == 'received' and not r.received).write({'received': True})
        #self.filtered(lambda r: r.state == 'attended' and not r.attended).write({'attended': True})
        #self.filtered(lambda r: r.state not in ['received','attended'] and r.received).write({'received': False})
        #self.filtered(lambda r: r.state not in ['received','attended'] and r.attended).write({'attended': False})
        ##self.filtered(lambda r: r.received).create_sale_order() #only created through button or through action
        for record in self :
            if record.state == 'received' :
                if not record.received :
                    record.received = True
            elif record.state == 'attended' :
                if not record.attended :
                    record.attended = True
            else :
                if record.received :
                    record.received = False
                if record.attended :
                    record.attended = False
    
    @api.depends('spots_from_line', 'procedure_id', 'line_ids', 'line_ids.spots', 'spot_ids')
    def _compute_special_spots(self) :
        for record in self :
            spots = record.procedure_id.planner_spots
            if record.spots_from_line :
                spots = record.line_ids.mapped('spots') or [0]
                spots = sum(spots)
            record.spots = spots or 1
            record.spot_ids._compute_available_spots()
            available_spots = (record.spot_ids.mapped('planner_ids') - record).mapped('spots')
            available_spots = sum(available_spots or [0])
            available_spots = min(record.spot_ids.mapped('spots') or [0]) - available_spots
            record.available_spots = available_spots
            record.has_available_spots = spots <= available_spots
    
    @api.depends('professional_id')
    def _compute_professional_id(self) :
        for record in self :
            procedure_ids = record.professional_id
            record.procedure_ids = procedure_ids and procedure_ids.procedure_ids or procedure_ids.procedure_ids.sudo().search([])
    
    @api.onchange('professional_id')
    def _onchange_professional_id(self) :
        if not self.professional_id :
            if self.spot_id :
                self.spot_id = False
            if self.procedure_id :
                self.procedure_id = False
    
    def compute_spot_ids_condition(self) :
        #self.ensure_one()
        #res = self.state not in ['cancel']
        res = 'cancel' not in self.mapped('state')
        return res
    
    def planner_spot_ids_condition(self) :
        res = self.filtered(lambda r: r.compute_spot_ids_condition())
        return res
    
    #@api.depends('professional_id', 'start', 'total_duration', 'spot_id')
    @api.depends('professional_id', 'start', 'total_duration', 'state')
    def _compute_spot_ids(self) :
        for record in self :
            old_spots = record.spot_ids
            if record.compute_spot_ids_condition() :
                start = record.start
                professional_id = record.professional_id.id
                spot = record.spot_id
                new_spots = record.spot_id
                if start and professional_id :
                    end = start + datetime.timedelta(hours=record.total_duration)
                    #if (not new_spots) or (end > new_spots.end) :
                    #    #new_spots |= self.env[spot._name].sudo().search([
                    #    new_spots = [
                    #        ('professional_id','=',professional_id),
                    #        ('start','>=',str(start)),
                    #        ('start','<',str(end)),
                    #        '|',
                    #            '&',
                    #                ('id','!=',spot.id),
                    #                ('available_spots','>',0),
                    #            '&',
                    #                ('id','=',spot.id),
                    #                ('available_spots','=',0),
                    #    ]
                    #    new_spots = self.env[spot._name].sudo().search(new_spots, order='start asc')
                    new_spots = spot.id
                    new_spots = [
                        ('professional_id','=',professional_id),
                        ('start','>=',str(start)),
                        ('start','<',str(end)),
                        #'|',
                        #    '&',
                        #        ('id','!=',new_spots),
                        #        ('available_spots','>',0),
                        #    ('id','=',new_spots),
                    ]
                    new_spots = self.env[spot._name].sudo().search(new_spots, order='start asc')
                #if old_spots != new_spots :
                record.spot_ids = [(6, 0, new_spots.ids)]
                (old_spots | new_spots)._compute_available_spots()
                if new_spots and ((not spot) or (spot not in new_spots)) :
                    record.spot_id = new_spots[0]
            else :
                record.spot_ids = [(5, 0, 0)]
                old_spots._compute_available_spots()
    
    @api.depends('procedure_id', 'line_ids', 'line_ids.product_id')
    def _compute_procedure_line(self) :
        #for record in self :
        #    if record.procedure_id :
        #        if record.procedure_id not in record.line_ids.mapped('product_id') :
        #            record.line_ids.write([(0, 0, {
        #                'product_id': record.procedure_id.id,
        #            })])
        #    else :
        #        procedures = record.line_ids.mapped('product_id')
        #        if len(procedures) > 0 :
        #            record.procedure_id = procedures[0]
        pass
    
    def _strict_spot_start_duration(self, force_change_start=True, change_duration=True) :
        #self.ensure_one()
        start = self.spot_id.start
        if change_duration or (not self.total_duration) :
            end = self.spot_id.end
            total_duration = (end - start).total_seconds() // 60.0
            total_duration = total_duration / 60.0
            if self.total_duration != total_duration :
                self.total_duration = total_duration
        if force_change_start :
            self.start = start
        else :
            #inside a depends loop, self._origin unnecesary
            if self.start != start :
                self.start = start
    
    @api.depends('spot_id')
    def _compute_start_duration(self) :
        for record in self :
            #record._onchange_spot_duration()
            if record.spot_id :
                spots = record.spot_ids
                if record.spot_id not in spots :
                    #start = record.spot_id.start
                    #end = record.spot_id.end
                    #total_duration = (end - start).seconds/3600.0
                    ##if record.total_duration != total_duration :
                    ##    record.total_duration = total_duration
                    #if record.start != start :
                    #    record.start = start
                    record._strict_spot_start_duration(force_change_start=False, change_duration=False)
                elif spots :
                    record.spot_id = spots.sorted(key=lambda r: r.start)[0]
            else :
                #record.total_duration = 0
                #record.start = False
                pass
    
    @api.onchange('spot_id')
    def _onchange_start_duration(self) :
        if self.spot_id :
            spots = self._origin.spot_ids
            if self.spot_id not in spots :
                #start = self.spot_id.start
                #end = self.spot_id.end
                #self.total_duration = (end - start).seconds/3600.0
                #self.start = start
                self._strict_spot_start_duration(change_duration=False)
            elif spots :
                self.spot_id = spots.sorted(key=lambda r: r.start)[0]
    
    def _strict_spots_start_duration(self, force_change_start=True, change_duration=True) :
        #self.ensure_one()
        start = self.spot_ids.mapped('start')
        if start :
            start = min(start)
            if change_duration or (not self.total_duration) :
                end = max(self.spot_ids.mapped('end'))
                total_duration = (end - start).total_seconds() // 60.0
                total_duration = total_duration / 60.0
                if self.total_duration != total_duration :
                    self.total_duration = total_duration
            if force_change_start :
                self.start = start
            else :
                #inside a depends loop, self._origin unnecesary
                if self.start != start :
                    self.start = start
    
    @api.depends('spot_ids')
    def _compute_spots_start_duration(self) :
        for record in self :
            if record.spot_ids :
                #start = min(record.spot_ids.mapped('start'))
                #end = min(record.spot_ids.mapped('end'))
                #total_duration = (end - start).total_seconds() // 60.0
                ##if record.total_duration != total_duration :
                ##    record.total_duration = total_duration / 60.0
                #if record.start != start :
                #    record.start = start
                record._strict_spots_start_duration(force_change_start=False, change_duration=False)
            else :
                #record.total_duration = 0
                #record.start = False
                pass
    
    @api.onchange('spot_ids')
    def _onchange_spots_start_duration(self) :
        if self.spot_ids :
            #start = min(self.spot_ids.mapped('start'))
            #end = min(self.spot_ids.mapped('end'))
            #total_duration = (end - start).total_seconds() // 60.0
            #self.total_duration = total_duration / 60.0
            #self.start = start
            self._strict_spots_start_duration()
    
    @api.depends('start')
    def _compute_date(self) :
        for record in self :
            start = record.start
            record.date = start and fields.Datetime.context_timestamp(self, start).date()
    
    @api.depends('start', 'total_duration')
    def _compute_end(self) :
        for record in self :
            start = record.start
            record.end = start and (start + datetime.timedelta(hours=record.total_duration))
    
    def update_from_self(self, values={}) :
        res = True
        if 'procedure_id' in values :
            for record in self :
                procedure = record.procedure_id.id
                procedures = record.line_ids.mapped('product_id').ids
                if procedure :
                    if procedure not in procedures :
                        record.write({'line_ids': [(0, 0, {'product_id': procedure})]})
                elif procedures :
                    record.write({'procedure_id': procedures[0]})
        return res
    
    def update_from_line(self, values={}) :
        res = True
        if 'product_id' in values :
            for record in self :
                procedures = record.line_ids.mapped('product_id')
                if (len(procedures) > 0) and (record.procedure_id.id not in procedures.ids) :
                    record.procedure_id = procedures[0]
        return res
    
    @api.model
    def create(self, values) :
        res = super().create(values)
        #if 'procedure_id' in values :
        #    #for record in res :
        #    #    procedure = record.procedure_id.id
        #    #    procedures = record.line_ids.mapped('product_id').ids
        #    #    if procedure :
        #    #        if procedure not in procedures :
        #    #            record.write({'line_ids': [(0, 0, {'product_id': procedure})]})
        #    #    elif procedures :
        #    #        record.write({'procedure_id': procedures[0]})
        #    res.update_from_self(values={'procedure_id'})
        res.update_from_self(values=set(values))
        return res
    
    def write(self, values) :
        res = super().write(values)
        if values.get('received') :
            self.receive_patient()
        #if 'procedure_id' in values :
        #    #for record in self :
        #    #    procedure = record.procedure_id.id
        #    #    procedures = record.line_ids.mapped('product_id').ids
        #    #    if procedure :
        #    #        if procedure not in procedures :
        #    #            record.write({'line_ids': [(0, 0, {'product_id': procedure})]})
        #    #    elif procedures :
        #    #        record.write({'procedure_id': procedures[0]})
        #    self.update_from_self(values={'procedure_id'})
        self.update_from_self(values=set(values))
        return res
    
    def unlink(self) :
        res = True
        spots = self.mapped('spot_ids')
        if self.env.context.get('force_unlink') :
            res = super().unlink()
        else :
            attended = self.filtered(lambda r: r.attended)
            attended.mark_cancel()
            res = super(PlannerPlanner, self - attended).unlink()
        spots._compute_available_spots()
        return res

class PlannerPlannerLine(models.Model) :
    _name = 'planner.planner.line'
    _description = 'Línea de Agenda'
    #_check_company_auto = True
    
    @api.model
    def _get_default_company_id(self) :
        company_id = self.env.company
        return company_id
    
    #company_id = fields.Many2one(comodel_name='res.company', string='Compañía', default=_get_default_company_id)
    planner_id = fields.Many2one(comodel_name='planner.planner', string='Agenda', required=True, ondelete='cascade')
    #sale_line_id = fields.Many2one(comodel_name='sale.order.line', string='Línea de Pedido de Venta')
    product_ids = fields.Many2many(comodel_name='product.product', string='Exámenes', compute='_compute_product_ids')
    product_id = fields.Many2one(comodel_name='product.product', string='Examen')
    spots = fields.Integer(string='Cupos', compute='_compute_product_id', store=True, readonly=False)
    price_unit = fields.Float(string='Precio', compute='_compute_product_id', store=True, readonly=False)
    
    #def _prepare_sale_order_line_values(self) :
    #    self.ensure_one()
    #    values = {
    #        'product_id': self.product_id.id,
    #        'price_unit': self.price_unit,
    #    }
    #    return values
    
    @api.depends('planner_id', 'planner_id.procedure_ids')
    def _compute_product_ids(self) :
        for record in self :
            record.product_ids = record.planner_id.procedure_ids
    
    @api.depends('product_id')
    def _compute_product_id(self) :
        for record in self :
            record.spots = record.product_id.planner_spots
            record.price_unit = record.product_id.lst_price
    
    @api.model
    def create(self, values) :
        res = super().create(values)
        #if 'product_id' in values :
        #    #for planner in res.mapped('planner_id') :
        #    #    procedures = planner.line_ids.mapped('product_id')
        #    #    if (len(procedures) > 0) and (planner.procedure_id.id not in procedures.ids) :
        #    #        planner.procedure_id = procedures[0]
        #    res.mapped('planner_id').update_from_line(values={'product_id'})
        res.mapped('planner_id').update_from_line(values=set(self._fields))
        return res
    
    def write(self, values) :
        res = super().write(values)
        #if 'product_id' in values :
        #    #for planner in self.mapped('planner_id') :
        #    #    procedures = planner.line_ids.mapped('product_id')
        #    #    if (len(procedures) > 0) and (planner.procedure_id.id not in procedures.ids) :
        #    #        planner.procedure_id = procedures[0]
        #    self.mapped('planner_id').update_from_line(values={'product_id'})
        self.mapped('planner_id').update_from_line(values=set(self._fields))
        return res
    
    def unlink(self) :
        planners = self.mapped('planner_id')
        values = self._fields
        res = super().unlink()
        #for planner in planners :
        #    procedures = planner.line_ids.mapped('product_id')
        #    if (len(procedures) > 0) and (planner.procedure_id.id not in procedures.ids) :
        #        planner.procedure_id = procedures[0]
        planners.update_from_line(values=set(values))
        return res

#class SaleOrderLine(models.Model) :
#    _inherit = 'sale.order.line'
#    
#    planner_line_id = fields.Many2one(comodel_name='planner.planner.line', string='Línea de Agenda')
