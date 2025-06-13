# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from pytz import timezone
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import zipfile
import base64
import json
from xml.dom.minidom import parseString
import time
import codecs
from xml.dom import minidom
from datetime import datetime, timedelta
import os
import sys
import time
import tempfile
import base64
import binascii

import json
import requests
from requests_toolbelt import MultipartEncoder
import logging
_logger = logging.getLogger(__name__)

### libreria de conexion con el SAT ###
import cfdiclient
from cfdiclient import Autenticacion
from cfdiclient import Fiel
#### Cambios 2025 ######
from cfdiclient import SolicitaDescargaEmitidos
from cfdiclient import SolicitaDescargaRecibidos
# --- #
from cfdiclient import Autenticacion
from cfdiclient import VerificaSolicitudDescarga
from cfdiclient import DescargaMasiva

### Libreria Prueba Consulta SAT - Alternativa y Manual Incluye los sig. Archivos ###
# from . import Download
# from . import Login
# from . import Request
# from . import Utils
# from . import Verify

### NOTAS ####
# SE DEBE USAR LA e.FIRMA, CONOCIDA ANTERIORMENTE COMO FIEL, NO USAR EL CSD
# ADEMAS SE DEBE USAR UN CERTIFICADO *REAL*, NO SE PUEDEN USAR CERTIFICADOS DE PRUEBA

# cfdi_account_dashboard_manager
# cfdi.account.dashboard.manager

class CFDIAccountDashboardManager(models.Model):
    _name = 'cfdi.account.dashboard.manager'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Dashboard Control de Documentos Descargados'
    _order = 'sequence desc' 
    
    def _get_current_company(self):
        return self.env.company.id

    color = fields.Integer(string='Color Index', default=9)
    name = fields.Char(string="Referencia")
    date = fields.Date('Fecha Consulta', default=fields.Date.today())
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda self: self.env.user.id)
    number_of_documents = fields.Integer('# Documentos SAT', help='Indica el No. de Documentos descargados en el SAT, tanto Pagos como Facturas.', )
    number_of_invoices = fields.Integer('# Facturas Cliente', help='Indica el No. de documentos encontrados en Odoo', )
    number_of_nc_invoices = fields.Integer('# Notas Credito Cliente', help='Indica el No. de documentos encontrados en Odoo', )
    number_of_supplier_inv = fields.Integer('# Facturas Proveedor', help='Indica el No. de documentos encontrados en Odoo', )
    number_of_nc_supplier_inv = fields.Integer('# Notas Credito Prov.', help='Indica el No. de documentos encontrados en Odoo', )
    number_of_payments = fields.Integer('# Pagos', help='Indica el No. de documentos encontrados en Odoo', )
    download_file = fields.Boolean('Descargar Archivo')
    datas_fname = fields.Char('File Name',size=256)
    file = fields.Binary("Zip XML's")
    periodo = fields.Char('Periodo Consulta', size=128)
    is_favorite = fields.Boolean('Favorito ?', default=True)
    download_type = fields.Selection([('emitidos','CFDI Emitidos'),('recibidos','CFDI Recibidos')], 'Tipo Descarga')
    id_solicitud = fields.Char('ID Solicitud de Descarga', size=128)
    status_solicitud = fields.Char('Estado de la Solicitud', size=128)
    download_pending = fields.Boolean('Descarga Pendiente')
    no_data = fields.Boolean('No se Encontro información')
    date_start = fields.Datetime('Fecha Inicial')
    date_stop = fields.Datetime('Fecha Final')
    package_pending = fields.Char('Paquetes Pendientes', size=256)
    sequence = fields.Integer('Secuencia', default=100)

    company_id = fields.Many2one('res.company', 'Empresa', default=_get_current_company)

    def write(self, vals):
        for rec in self:
            if 'is_favorite' in vals and vals['is_favorite'] == False:
                vals.update({'sequence': rec.id})
        return super(CFDIAccountDashboardManager, self).write(vals)


    # def check_download_pending(self, file_globals, id_solicitud):
    #     wizard_download_obj = self.env['account.cfdi.multi.download']

    #     paquete_b64 = "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"
    #     date_act = fields.Date.today()
    #     datas_fname = "Documentos XML %s " % date_act+".zip"
    #     codigo_estado_solicitud = "5000"
    #     status_solicitud = "Al Millonaso"
    #     no_data = False
    #     download_pending = False
    #     result_download_request = {}
    #     paquete_final, zip_pth = wizard_download_obj.zip_b64_str_to_physical_file(paquete_b64, 'zip', 'descarga_paquete')
    #     if paquete_b64:
    #         result_download_request = {
    #             'download_pending': False,
    #             'status_solicitud': status_solicitud,
    #             'no_data': no_data,
    #             'datas_fname': datas_fname,
    #             'file': paquete_b64,
    #             'number_of_documents': 5,
    #         }
    #     return result_download_request

    def check_download_pending(self, file_globals, id_solicitud):
        ## Regresa los Siguientes Valores
        # datas_fname
        # file
        # status_solicitud
        # download_pending
        # no_data
        _logger.info('\n:::::::::::::::::::::::::: Verificando Descarga Pendiente ( %s ).....' % self.name)
        result_download_request = {
                
                }
        date_act = fields.Date.today()
        datas_fname = "Documentos XML %s " % date_act+".zip"

        wizard_download_obj = self.env['account.cfdi.multi.download'].create({'company_id': self.company_id.id})
        data_solicitud_check = wizard_download_obj.get_download_check_request(file_globals, id_solicitud)

        _logger.info("\n################### data_solicitud_check %s " % data_solicitud_check)
        codigo_estado_solicitud = data_solicitud_check['codigo_estado_solicitud']
        estado_solicitud = data_solicitud_check['estado_solicitud'] # 1 Pendiente 3 Lista
        _logger.info("\n################ estado_solicitud %s " % estado_solicitud)
        numero_cfdis = 0.0
        status_solicitud = data_solicitud_check['mensaje']
        paquete_b64 = False
        no_data = True
        if codigo_estado_solicitud != '5000':
            _logger.info('\n:::::::::::::::::::::::::: La Solicitud aun no esta lista( %s ).....' % self.name)
            result_download_request = {
                'download_pending': True,
                'status_solicitud': 'No se encontró información',
            }
            return result_download_request
        else:
            if estado_solicitud == '3':
                download_pending = False # Si fue Aceptada entonces no esta pendiente de Aprobarse
                numero_cfdis = data_solicitud_check['numero_cfdis']
                number_of_documents = numero_cfdis ### Total Descargado en el SAT
                _logger.info('\n:::::::::::::::::::::::::: Solicitud Aceptada Lista para Descarga ( %s ).....' % self.name)
                paquetes = list(data_solicitud_check['paquetes'])
                _logger.info("\n################ PAQUETES %s " % paquetes)

                ### Comenzamos con la Descarga de los Archivos ###
                package_pending = ""
                if paquetes:
                    package_pending = str(paquetes).replace("'","").replace("[","").replace("]","").replace(" ","")
                    try:
                        data_solicitud_final_download = wizard_download_obj.get_download_final_data_request(file_globals, paquetes[0])
                        if 'mensaje' in data_solicitud_final_download and data_solicitud_final_download['mensaje']:
                            status_solicitud = data_solicitud_final_download['mensaje']

                        paquete_b64 = data_solicitud_final_download['paquete_b64']                    
                        ### Volcando Resultado al Temporal ###
                        # paquete_final, zip_pth = wizard_download_obj.zip_b64_str_to_physical_file(paquete_b64, 'zip', 'descarga_paquete')
                        no_data = False
                    except:
                        download_pending = True
                        no_data = True
                        status_solicitud = 'Ocurrio un Error durante la descarga de los paquetes.'
                else:
                    status_solicitud = 'No se encontró la información'
                    no_data = True
                if paquete_b64:
                    result_download_request = {
                        'download_pending': False ,
                        'status_solicitud': status_solicitud,
                        'no_data': no_data,
                        'datas_fname': datas_fname,
                        'file': paquete_b64,
                        'number_of_documents': number_of_documents,
                        'color': 11,
                        'package_pending': package_pending,
                        'sequence': self.id,
                    }
                else:
                    result_download_request = {
                        'download_pending': False if no_data == True else True,
                        'status_solicitud': status_solicitud,
                        'no_data': no_data,
                        'package_pending': package_pending,
                        'number_of_documents': number_of_documents,
                        'datas_fname': datas_fname,
                    }
            else:
                if estado_solicitud == '1':
                    download_pending = True
                    numero_cfdis = 0 ### Total Descargado en el SAT
                    _logger.info('\n################ Solicitud Aceptada, pero aun no lista para Descarga ( %s ).....' % self.name)
                    status_solicitud = status_solicitud+", SAT - preparando archivo."
                    result_download_request = {
                        'download_pending': True,
                        'status_solicitud': status_solicitud,
                        'no_data': True,
                        'number_of_documents': 0,
                    }
                elif estado_solicitud == '2':
                    download_pending = True
                    numero_cfdis = 0 ### Total Descargado en el SAT
                    _logger.info('\n################ Solicitud Aceptada, pero aun no lista para Descarga ( %s ).....' % self.name)
                    status_solicitud = status_solicitud+", SAT - preparando archivo."
                    result_download_request = {
                        'download_pending': True,
                        'status_solicitud': status_solicitud,
                        'no_data': True,
                        'number_of_documents': 0,
                    }
                else:
                    download_pending = False
                    status_solicitud = 'No se encontró la información'
                    no_data = True
                    result_download_request = {
                        'download_pending': False,
                        'status_solicitud': status_solicitud,
                        'no_data': True,
                        'number_of_documents': 0,
                        'sequence': self.id,
                        'color': 9,
                        'is_favorite': False
                    }


            return result_download_request

    def recovery_packages_from_sat(self, file_globals, package_pending):
        ## Regresa los Siguientes Valores
        # datas_fname
        # file
        # status_solicitud
        # download_pending
        # b64
        _logger.info('\n:::::::::::::::::::::::::: Verificando Descarga de Paquetes Pendiente ( %s ).....' % self.name)
        _logger.info('\n:::::::::::::::::::::::::: Paquetes Pendiente ( %s ).....' % package_pending)
        result_download_request = {
                
                }
        date_act = fields.Date.today()
        datas_fname = "Documentos XML %s " % date_act+".zip"

        wizard_download_obj = self.env['account.cfdi.multi.download'].create({'company_id': self.company_id.id})
        status_solicitud = ""
        paquete_b64 = False
        no_data = True

        download_pending = False # Si fue Aceptada entonces no esta pendiente de Aprobarse
        paquetes = package_pending.split(',')
        if paquetes:
            try:
                _logger.info("\n########## DESCARGANDO EL PAQUETE %s >>>>>>>>>>> " % paquetes[0])
                data_solicitud_final_download = wizard_download_obj.get_download_final_data_request(file_globals, paquetes[0])
                if 'mensaje' in data_solicitud_final_download and data_solicitud_final_download['mensaje']:
                    status_solicitud = data_solicitud_final_download['mensaje']

                paquete_b64 = data_solicitud_final_download['paquete_b64']                    
                ### Volcando Resultado al Temporal ###
                #paquete_final, zip_pth = wizard_download_obj.zip_b64_str_to_physical_file(paquete_b64, 'zip', 'descarga_paquete')
                no_data = False
            except:
                download_pending = True
                no_data = True
                status_solicitud = 'Ocurrio un Error durante la descarga de los paquetes.'
        else:
            status_solicitud = 'No se encontró la información'
            no_data = True
        if paquete_b64:
            result_download_request = {
                'download_pending': False ,
                'status_solicitud': status_solicitud,
                'no_data': no_data,
                'datas_fname': datas_fname,
                'file': paquete_b64,
                'color': 11,
                'sequence': self.id,
            }
        else:
            result_download_request = {
                'download_pending': True,
                'status_solicitud': status_solicitud,
                'no_data': no_data,
                'datas_fname': datas_fname,
            }


        return result_download_request


    
    def action_download(self):
        _logger.info("\n:::::::::::::::::::::::::: Descargando Datos desde el Dashboard. Usuario: %s >>>>>>>  " % self.env.user.name_get()[0][1])
        for rec in self:
            context = self._context
            context = dict(context)
            ### Si no queremos que se descargue el paquete enviamos dentro del contexto la clave "download_stop":True
            # context.update({'download_stop':True})
            ### Varibales que contienen el Zip ara descargar ####
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            file_url = base_url+"/web/content?model=cfdi.account.dashboard.manager&field=file&filename_field=datas_fname&id=%s&&download=true" % (rec.id,)

            if rec.no_data and rec.download_pending == False:
                raise UserError("No existe información relacionada con esta Consulta.")
            if rec.download_pending and rec.id_solicitud:
                wizard_download_obj = self.env['account.cfdi.multi.download'].create({'company_id': self.company_id.id})
                file_globals = wizard_download_obj._get_file_globals_download()
                if rec.download_pending and not rec.package_pending:
                    result_download_request = self.check_download_pending(file_globals, rec.id_solicitud)
                else:
                    result_download_request = self.recovery_packages_from_sat(file_globals, rec.package_pending)
                if result_download_request:
                    rec.write(result_download_request)
                    if 'file' in result_download_request and result_download_request['file']:
                        if 'download_stop' in context and context['download_stop']:
                            rec.write({'color': 11,'sequence': 100+rec.id})
                            return {'type': 'ir.actions.act_window_close'}
                        else:
                            rec.write({'is_favorite': False})
                            return {
                                     'type': 'ir.actions.act_url',
                                     'url': file_url,
                                     'target': 'new'
                                    } 
                    else:
                        return {
                                 'name': 'Resultado de Consutla SAT',
                                 'view_mode': 'form',
                                 'view_id': self.env.ref('l10n_mx_auditor_sat.cfdi_account_dashboard_manager_form').id,
                                 'res_model': 'cfdi.account.dashboard.manager',
                                 'context': "{}", # self.env.context
                                 'type': 'ir.actions.act_window',
                                 'res_id': rec.id,
                                }
            rec.compute_documents_from_period()
            rec.write({'color': 10})
            if rec.is_favorite:
                rec.write({'is_favorite': False})
            ### Si Desde un Inicio todo fue correcto regresar el Resultado ###
            return {
                    'type': 'ir.actions.act_url',
                    'url': file_url,
                    'target': 'new'
            }

    #### Consulta Autmatica de Descargas
    @api.model
    def _run_download_pending_package_from_sat(self):
        _logger.info("\n:::::::::::::::::::::::::: Descargando Paquetes Pendientes XML desde el SAT. Fecha: %s >>>>>>>  " % fields.Date.context_today(self))
        records_pending = self.search([
            ('download_pending', '=', True),
            ('id_solicitud', '!=', False)])
        for consulta in records_pending:
            _logger.info("\n####################### Procesando la Consulta %s " % consulta.name)
            write_date = consulta.write_date
            date_act = fields.Datetime.now()
            minutes_diff = date_act - write_date
            difference_between_request = minutes_diff.seconds

            ### Conviritendo las Unidades de Medida de Tiempo para enviarlas al Log ###
            difference_in_unit_of_measure = float(difference_between_request)
            unit_of_measure_time = 'segundos'
            if difference_between_request >= 60.0:
                difference_in_unit_of_measure = float(difference_between_request) / 60.0
                unit_of_measure_time = 'minutos'
                if difference_in_unit_of_measure >= 60.0:
                    difference_in_unit_of_measure = float(difference_in_unit_of_measure) / 60.0
                    unit_of_measure_time = 'horas'
            _logger.info("\n####################### Tiempo Transcurrido desde la ultima consulta %s %s" % (round(difference_in_unit_of_measure,4),unit_of_measure_time))
            
            ### Comparando la diferencia entre Consultas, tomando como parametro que deben tener mas de 2 horas de diferencia entre consultas ###
            time_to_download = 7200 # Segundos = 2 Horas
            if difference_between_request >= time_to_download:
                ### Si la compañia esta marcada con consultas automatizadas ####
                if consulta.company_id.download_automatically:
                    ### Ejecutamos el metodo de consulta sin descargar paquetes del navegador ###
                    _logger.info("\n####################### Descargando la Solicitud con ID Odoo %s " % consulta.id)
                    _logger.info("\n####################### ID Solicitud SAT %s " % consulta.id_solicitud)
                    consulta.with_context(download_stop=True).action_download()
                else:
                    _logger.info("\n####################### La Compañia %s no esta autorizada para descargar automaticamente los paquetes del SAT. Consulta ID %s " % (consulta.user_id.company_id.name,consulta.id))
        # for move in records:
        #     date = None
        #     if move.reverse_date and (not self.env.user.company_id.period_lock_date or move.reverse_date > self.env.user.company_id.period_lock_date):
        #         date = move.reverse_date
        #     move.reverse_moves(date=date, auto=True)

    
    def compute_documents_from_period(self):
        payment_obj = self.env['account.payment']
        account_invoice_obj = self.env['account.move']
        for rec in self:
            _logger.info("\n:::::::::::::::::::::::::: Consultando los Documentos en Odoo >>>>> ")
            date_start = rec.date_start
            date_stop = rec.date_stop
            number_of_invoices = 0
            number_of_nc_invoices = 0
            number_of_supplier_inv = 0
            number_of_nc_supplier_inv = 0
            number_of_payments = 0
            ### Comenzamos la Busqueda ####
            ######### Facturas de Cliente ##########
            number_of_invoices = account_invoice_obj.search_count([('move_type','=','out_invoice'),
                                                                   ('state','in',('open','paid')),
                                                                   ('l10n_mx_edi_cfdi_uuid','!=',False),
                                                                   ('l10n_mx_edi_post_time','>=',date_start),
                                                                   ('l10n_mx_edi_post_time','<=',date_stop)])
            rec.number_of_invoices = number_of_invoices
            ######### Notas de Credito de Cliente ##########
            number_of_nc_invoices = account_invoice_obj.search_count([('move_type','=','out_refund'),
                                                                   ('state','in',('open','paid')),
                                                                   ('l10n_mx_edi_cfdi_uuid','!=',False),
                                                                   ('l10n_mx_edi_post_time','>=',date_start),
                                                                   ('l10n_mx_edi_post_time','<=',date_stop)])
            rec.number_of_nc_invoices = number_of_nc_invoices
            ######### Pagos ##########
            number_of_payments = payment_obj.search_count([
                                                                   ('state','in',('posted','reconciled','sent')),
                                                                   ('l10n_mx_edi_cfdi_uuid','!=',False),
                                                                   ('date','>=',date_start),
                                                                   ('date','<=',date_stop)])
            rec.number_of_payments = number_of_payments
            ######### Facturas de Proveedor ##########
            date_start_supl = str(date_start)[0:10]
            date_stop_supl = str(date_stop)[0:10]
            number_of_supplier_inv = account_invoice_obj.search_count([('move_type','=','in_invoice'),
                                                                   ('state','in',('open','paid')),
                                                                   ('invoice_date','>=',date_start_supl),
                                                                   ('invoice_date','<=',date_stop_supl)])
            rec.number_of_supplier_inv = number_of_supplier_inv
            ######### Notas de Credito de Proveedor ##########
            number_of_nc_supplier_inv = account_invoice_obj.search_count([('move_type','=','in_refund'),
                                                                   ('state','in',('open','paid')),
                                                                   ('invoice_date','>=',date_start_supl),
                                                                   ('invoice_date','<=',date_stop_supl)])
            rec.number_of_nc_supplier_inv = number_of_nc_supplier_inv

        return True
    
class AccountCFDIMultiDownload(models.TransientModel):
    _name = 'account.cfdi.multi.download'
    _description = 'Asistente Descarga SAT'

    def _get_current_company(self):
        return self.env.company.id

    date_start = fields.Datetime('Fecha Inicial', default=lambda self: datetime.strptime(str(fields.Date.context_today(self))+' 06:00:00','%Y-%m-%d %H:%M:%S'))
    date_stop = fields.Datetime('Fecha Final', default=lambda self: datetime.strptime(str(fields.Date.context_today(self))+' 23:59:59','%Y-%m-%d %H:%M:%S'))
    download_type = fields.Selection([('emitidos','CFDI Emitidos'),('recibidos','CFDI Recibidos')], 'Tipo Descarga')
    name = fields.Char(string="Referencia", default="Consulta Documentos CFDI "+str(fields.Date.today()))

    date_start_prev = fields.Datetime('Fecha Inicial Prev.')
    date_stop_prev = fields.Datetime('Fecha Final Prev.')
    download_type_prev = fields.Selection([('emitidos','CFDI Emitidos'),('recibidos','CFDI Recibidos')], 'Tipo Descarga Prev.')

    company_id = fields.Many2one('res.company', 'Empresa', default=_get_current_company)

    
    def b64str_to_tempfile(self, b64_str=None, file_suffix=None, file_prefix=None):
        """
        @param b64_str : Text in Base_64 format for add in the file
        @param file_suffix : Sufix of the file
        @param file_prefix : Name of file in TempFile
        """
        (fileno, fname) = tempfile.mkstemp(file_suffix, file_prefix)
        f = open(fname, 'wb')
        f.write(base64.decodebytes(b64_str or str.encode('')))
        f.close()
        os.close(fileno)
        return fname

    def zip_b64_str_to_physical_file(self, b64_str, file_extension, prefix='data'):
        _logger.info("\n####################### zip_b64_str_to_physical_file >>>>>>>>>>> ")
        _logger.info("\n####################### file_extension %s " % file_extension)
        _logger.info("\n####################### prefix %s " % prefix)
        #certificate_lib = self.env['facturae.certificate.library']
        b64_temporal_route = self.b64str_to_tempfile(base64.decodebytes(b''), 
                                                          file_suffix='.%s' % file_extension, 
                                                          file_prefix='odoo__%s__' % prefix)
        _logger.info("\n### b64_temporal_route %s " % b64_temporal_route)
        ### Guardando la Cadena Original ###
        f = open(b64_temporal_route, 'wb')
        f.write(base64.b64decode(b64_str))
        f.close()

        file_result = open(b64_temporal_route, 'rb').read()
        
        return file_result, b64_temporal_route

    def b64_str_to_physical_file(self, b64_str, file_extension, prefix='data'):
        _logger.info("\n####################### b64_str_to_physical_file >>>>>>>>>>> ")
        _logger.info("\n####################### file_extension %s " % file_extension)
        _logger.info("\n####################### prefix %s " % prefix)
        #certificate_lib = self.env['facturae.certificate.library']
        b64_temporal_route = self.b64str_to_tempfile(base64.encodebytes(b''), 
                                                          file_suffix='.%s' % file_extension, 
                                                          file_prefix='odoo__%s__' % prefix)
        _logger.info("\n### b64_temporal_route %s " % b64_temporal_route)
        ### Guardando la Cadena Original ###
        f = open(b64_temporal_route, 'wb')
        f.write(base64.decodebytes(b64_str or str.encode('')))
        f.close()

        file_result = open(b64_temporal_route, 'rb').read()
        
        return file_result, b64_temporal_route
    

    
    def _get_file_globals_download(self):
        company_user = self.company_id
        if not company_user.certificate_file:
            raise UserError("No se ha encontrado una Firma Electronica Configurada.")
        ### Variables Globales de los Metodos de Facturacion ###
        certificate_file, cf_pth = self.b64_str_to_physical_file(company_user.certificate_file, 'cer', 'cer')
        certificate_key_file, kf_pth = self.b64_str_to_physical_file(company_user.certificate_key_file, 'key', 'key')
        certificate_password = company_user.certificate_password
        # certificate_file_pem, cpm_path = self.b64_str_to_physical_file(company_user.certificate_file_pem, 'cer.pem', 'cer_pem')
        # certificate_key_file_pem, kpm_path = self.b64_str_to_physical_file(company_user.certificate_key_file_pem, 'key.pem', 'key_pem')
        # certificate_pfx_file, pfx_path = self.b64_str_to_physical_file(company_user.certificate_pfx_file, 'pfx', 'pfx')

        file_globals = {
                        'certificate_file': certificate_file,
                        'certificate_key_file': certificate_key_file,
                        'certificate_password': certificate_password,
                        'temporary_path_files': [
                                                    cf_pth,
                                                    kf_pth,
                                                   ]
                        # 'certificate_file_pem': certificate_file_pem,
                        # 'certificate_key_file_pem': certificate_key_file_pem,
                        # 'certificate_pfx_file': certificate_pfx_file,
                        # 'temporary_path_files': [
                        #                             cf_pth,
                        #                             kf_pth,
                        #                             cpm_path,
                        #                             kpm_path,
                        #                             pfx_path,
                        #                            ]
                        }
        ### Instancia Libreria FIEL ###
        fiel = Fiel(file_globals['certificate_file'], file_globals['certificate_key_file'],
            file_globals['certificate_password'])

        file_globals.update({
                        'fiel': fiel,
            })
        ### TOKEN ####
        file_globals.update({
            'token': self.get_token_cfdi_client( 
                file_globals['certificate_file'], file_globals['certificate_key_file'],
                file_globals['certificate_password'], fiel
                ),
            })
        return file_globals
            
    
    def get_token_cfdi_client(self, cer_der, key_der, fiel_pas, fiel_instance):
        token = ""

        FIEL_PAS = fiel_pas
        cer_der = cer_der
        key_der = key_der
        fiel = fiel_instance

        ### Instancia Libreria Encargada de Autentificarse con la FIEL ###
        auth = Autenticacion(fiel)

        token = auth.obtener_token()

        _logger.info("\n################ token %s " % token)

        return token

    
    def get_download_request(self, file_globals, download_type='emitidos'):
        _logger.info("\n::::: Creando una Solicitud de Descarga")
        
        
        #for key in file_globals:
        #    _logger.info("\n%s: %s" % (key, file_globals[key]))
        #_logger.info("\nfile_globals: %s" % file_globals)
        
        for rec in self:
            company_user = rec.company_id
            token = file_globals['token']
            rfc_solicitante = company_user.vat
            # date_start = str(rec.date_start).split('-')
            # date_stop = str(rec.date_stop).split('-')
            # fecha_inicial = datetime(int(date_start[0]), int(date_start[1]), int(date_start[2]))
            # fecha_final = datetime(int(date_stop[0]), int(date_stop[1]), int(date_stop[2]), 23, 59, 59)
            fecha_inicial = rec.date_start
            fecha_final = rec.date_stop
            ### Convertion a Zona Horaria Usuario ####
            fecha_inicial = fields.Datetime.context_timestamp(self, timestamp=fecha_inicial)
            fecha_final = fields.Datetime.context_timestamp(self, timestamp=fecha_final)

            _logger.info("\n################ fecha_inicial %s " % fecha_inicial)
            _logger.info("\n################ fecha_final %s " % fecha_final)
            rfc_emisor = company_user.vat
            rfc_receptor = company_user.vat

            FIEL_PAS = file_globals['certificate_password']
            cer_der = file_globals['certificate_file']
            key_der = file_globals['certificate_key_file']

            fiel = file_globals['fiel']

            _logger.info("\n################ rfc_solicitante %s " % rfc_solicitante)
            _logger.info("\n################ rfc_emisor %s " % rfc_emisor)
            _logger.info("\n################ rfc_receptor %s " % rfc_receptor)

            ### Instancia Libreria Encargada de Solicitar Descarga ###
            #### Cambios 2025 ######

            if rec.download_type_prev == 'emitidos':
                descarga = SolicitaDescargaEmitidos(fiel)
            elif rec.download_type_prev == 'recibidos':
                descarga = SolicitaDescargaRecibidos(fiel)
            # ---- #

            result = {}
            return_data_solicitud = {}
            # {'mensaje': 'Solicitud Aceptada', 'cod_estatus': '5000', 
            #  'id_solicitud': 'be2a3e76-684f-416a-afdf-0f9378c346be'}
            
            #### Cambios 2025 ######
            try:
                # Realizar la solicitud según el tipo
                if download_type == 'emitidos':
                    # token, 
                    # rfc_solicitante, 
                    # fecha_inicial, 
                    # fecha_final,
                    # rfc_emisor=None, 
                    # rfc_receptor=None, 
                    # tipo_solicitud='CFDI',
                    # tipo_comprobante=None, 
                    # estado_comprobante=None,
                    # rfc_a_cuenta_terceros=None, 
                    # complemento=None, 
                    # uuid=None
                    _logger.info("\n############### Solicitando CFDI Emitidos >>> ")
                    result = descarga.solicitar_descarga(
                        token=token, 
                        rfc_solicitante=rfc_solicitante, 
                        fecha_inicial=fecha_inicial, 
                        fecha_final=fecha_final, 
                        rfc_emisor=rfc_emisor,
                        tipo_solicitud='CFDI',  # Agregar tipo_solicitud explícitamente
                        estado_comprobante='Vigente'
                    )
                else:  # recibidos
                    # token, 
                    # rfc_solicitante, 
                    # fecha_inicial, 
                    # fecha_final,
                    # rfc_emisor=None, 
                    # rfc_receptor=None, 
                    # tipo_solicitud='CFDI',
                    # tipo_comprobante=None, 
                    # estado_comprobante=None,
                    # rfc_a_cuenta_terceros=None, 
                    # complemento=None, 
                    # uuid=None
                    _logger.info("\n############### Creando instancia para CFDI Recibidos")
                    
                    _logger.info("\n############### Solicitando CFDI Recibidos")
                    result = descarga.solicitar_descarga(
                        token=token,
                        rfc_solicitante=rfc_solicitante,
                        fecha_inicial=fecha_inicial,
                        fecha_final=fecha_final,
                        rfc_emisor=None,  # Para recibidos, no especificar emisor específico
                        rfc_receptor=rfc_solicitante,
                        tipo_solicitud='CFDI',
                        tipo_comprobante='I',
                        estado_comprobante='Vigente'
                    )
                
                _logger.info(f"\n############### Resultado de solicitud: {result}")
                
            except Exception as e:
                _logger.error(f"\n############### Error en solicitud de descarga: {e}")
                return {
                        'error': f'Error en solicitud de descarga: {str(e)}',
                        'id_solicitud': '',
                        'codigo_estado_solicitud': '',
                        'estado_solicitud': '4',
                        }
            # ---- #
            # if download_type == 'emitidos':
            #     _logger.info( "\n############### CFDI Emitidos >>> ")
            #     result = descarga.solicitar_descarga(token, rfc_solicitante, fecha_inicial, fecha_final, rfc_emisor=rfc_emisor)
            #     _logger.info(result)
            # # Recibidos
            # else:
            #     _logger.info( "\n############### CFDI Recibidos >>> ")
            #     result = descarga.solicitar_descarga(token, rfc_solicitante, fecha_inicial, fecha_final, rfc_receptor=rfc_receptor)
            #     _logger.info(result)
            #raise ValidationError("Pausa2")
            if result:
                id_solicitud = ""
                status_solicitud = ""
                if 'mensaje' in result:
                    status_solicitud = result['mensaje']
                if 'id_solicitud' in result:
                    id_solicitud = result['id_solicitud']
                if 'cod_estatus' in result:
                    cod_estatus = result['cod_estatus']
                return_data_solicitud = {
                                            'id_solicitud': id_solicitud,
                                            'status_solicitud': status_solicitud,
                                            'cod_estatus': cod_estatus,
                                        }
            _logger.info("\n::::: Resultado Final Solicitud %s" % return_data_solicitud)
            return return_data_solicitud

    def get_download_check_request(self, file_globals, id_solicitud):
        _logger.info("\n:::::::::::::::::::::::::: Verificando  una Solicitud de Descarga")
        _logger.info("\n:::::::::::::::::::::::::: ID Solicitud %s  " % id_solicitud)
        company_user = self.company_id
        token = file_globals['token']
        rfc_solicitante = company_user.vat

        fiel = file_globals['fiel']

        ### Instancia Libreria Encargada de Verificar la Descarga ###
        v_descarga = VerificaSolicitudDescarga(fiel)

        result = {}
        result = v_descarga.verificar_descarga(token, rfc_solicitante, id_solicitud)
        _logger.info("\n################ Resultado Verificacion %s  " % result)
        _logger.info("\n################ Resultado Verificacion a Dict. %s  " % dict(result))
        # {'estado_solicitud': '3', 'numero_cfdis': '8', 'cod_estatus': '5000', 'paquetes': ['a4897f62-a279-4f52-bc35-03bde4081627_01'], 'codigo_estado_solicitud': '5000', 'mensaje': 'Solicitud Aceptada'}
        return dict(result)

    def get_download_final_data_request(self, file_globals, id_paquete):
        _logger.info("\n:::::::::::::::::::::::::: Descargando el Paquete")
        _logger.info("\n:::::::::::::::::::::::::: ID Paquete %s >>> " % id_paquete)
        company_user = self.company_id
        token = file_globals['token']
        rfc_solicitante = company_user.vat

        fiel = file_globals['fiel']

        ### Instancia Libreria Encargada de la Descarga del SAT ###
        descarga = DescargaMasiva(fiel)

        result = {}
        result = descarga.descargar_paquete(token, rfc_solicitante, id_paquete)
        # {'estado_solicitud': '3', 'numero_cfdis': '8', 'cod_estatus': '5000', 'paquetes': ['a4897f62-a279-4f52-bc35-03bde4081627_01'], 'codigo_estado_solicitud': '5000', 'mensaje': 'Solicitud Aceptada'}
        return  dict(result)

    
    def execute_download(self):
        for rec in self:
            ### Obteniendo las Variables Globales para obtener los datos Fiscales ###
            file_globals = rec._get_file_globals_download()
            _logger.info("\n:::::::::::::::::::::::::: Comenzando la Descarga de Documentos %s" % rec.download_type.upper())
            ### Marcamos la Consulta Anterior para Comparar ####
            if not rec.date_start_prev:
                rec.date_start_prev = rec.date_start
                rec.date_stop_prev = rec.date_stop
                rec.download_type_prev = rec.download_type
            else:
                if rec.date_start_prev == rec.date_start and rec.date_stop_prev == rec.date_stop and\
                    rec.download_type_prev == rec.download_type:
                    raise UserError("Esta Consulta ya fue generada en el Sistema Consulta el Tablero Historico.")
            ### El SAT Valida que solo existan 2 consultas con los mismos parametros ###
            previous_request = self.constraint_unique_request(rec.date_start, rec.date_stop)
            if previous_request:
                raise UserError("Esta consulta ya se realizo con anterioridad por lo cual el SAT realizo un bloqueo temporal, prueba con un periodo distinto.")
            #### Inicializamos las Variables ####
            datas_fname = ""
            date_act = fields.Date.today()
            _logger.info("\n### Fecha Actual %s " % date_act)
            datas_fname = "Documentos XML %s " % date_act+".zip"
            # rec.write({
            #         'datas_fname':datas_fname,
            #         'file':base64.decodebytes(b'')
            #     })
            user_id = self.env.user.id
            number_of_documents = 0.0
            number_of_invoices = 0.0
            number_of_nc_invoices = 0.0
            number_of_supplier_inv = 0.0
            number_of_nc_supplier_inv = 0.0
            number_of_payments = 0.0

            ### COMENZANDO LA DESCARGA DE LOS DOCUMENTOS ###
            data_solicitud = rec.get_download_request(file_globals, rec.download_type)
            _logger.info("\n################ data_solicitud %s " % data_solicitud)
            cod_estatus = data_solicitud['cod_estatus']
            id_solicitud = ""
            status_solicitud = ""
            paquete_b64 = base64.decodebytes(b'')
            download_pending = True
            no_data = False
            file_ready_for_download = False
            package_pending = ""
            if cod_estatus != '5000':
                _logger.info('\n################ La Solicitud se encuentra en Proceso ( %s ).....' % rec.name)
                status_solicitud = data_solicitud['status_solicitud']
            else:
                id_solicitud = data_solicitud['id_solicitud']
                _logger.info("\n################ SOLICITUD ACEPTADA >>> ")
                _logger.info("\n################ CREAMOS METODO DESCARGA >>>  ")
                data_solicitud_check = rec.get_download_check_request(file_globals, id_solicitud)
                _logger.info("\n################ data_solicitud_check %s " % data_solicitud_check)
                codigo_estado_solicitud = data_solicitud_check['codigo_estado_solicitud']
                estado_solicitud = data_solicitud_check['estado_solicitud'] # 1 Pendiente y 3 Lista
                _logger.info("\n################ estado_solicitud %s " % estado_solicitud)
                numero_cfdis = 0.0
                status_solicitud = data_solicitud_check['mensaje']
                if codigo_estado_solicitud != '5000':
                    _logger.info('\n La Solicitud aun no esta lista( %s ).....' % rec.name)
                else:
                    #### Cambios 2025 ######
                    # Interpretar estado para logging
                    estados_map = {
                                        '0': 'Token inválido',
                                        '1': 'Aceptada',
                                        '2': 'En proceso', 
                                        '3': 'Terminada',
                                        '4': 'Error',
                                        '5': 'Rechazada',
                                        '6': 'Vencida'
                                    }
                    # ---- #
                    if estado_solicitud == '3':
                        download_pending = False # Si fue Aceptada entonces no esta pendiente de Aprobarse
                        numero_cfdis = data_solicitud_check['numero_cfdis']
                        number_of_documents = numero_cfdis ### Total Descargado en el SAT
                        _logger.info('\n################ Solicitud Aceptada Lista para Descarga ( %s ).....' % rec.name)
                        paquetes = list(data_solicitud_check['paquetes'])
                        _logger.info("\n################ PAQUETES %s " % paquetes)

                        ### Comenzamos con la Descarga de los Archivos ###
                        if paquetes:
                            package_pending = str(paquetes).replace("'","").replace("[","").replace("]","").replace(" ","")
                            try:
                                data_solicitud_final_download = rec.get_download_final_data_request(file_globals, paquetes[0])
                                if 'mensaje' in data_solicitud_final_download and data_solicitud_final_download['mensaje']:
                                    status_solicitud = data_solicitud_final_download['mensaje']

                                paquete_b64 = data_solicitud_final_download['paquete_b64']                    
                                ### Volcando Resultado al Temporal ###
                                # paquete_final, zip_pth = self.zip_b64_str_to_physical_file(paquete_b64, 'zip', 'descarga_paquete')
                                no_data = False
                                file_ready_for_download = True
                            except:
                                download_pending = True
                                no_data = True
                                status_solicitud = 'Ocurrio un Error durante la descarga de los paquetes.'
                                file_ready_for_download = False
                        else:
                            status_solicitud = 'No se encontró la información'
                            no_data = True
                    else:
                        if estado_solicitud == '1':
                            download_pending = True
                            numero_cfdis = 0.0
                            number_of_documents = numero_cfdis ### Total Descargado en el SAT
                            _logger.info('\n################ Solicitud Aceptada, pero aun no lista para Descarga ( %s ).....' % rec.name)
                            status_solicitud = status_solicitud+", SAT - preparando archivo."
                            no_data = True
                        elif estado_solicitud == '2':
                            download_pending = True
                            numero_cfdis = 0.0
                            number_of_documents = numero_cfdis ### Total Descargado en el SAT
                            _logger.info('\n################ Solicitud Aceptada, pero aun no lista para Descarga ( %s ).....' % rec.name)
                            status_solicitud = status_solicitud+", SAT - preparando archivo."
                            no_data = True

                        #### Cambios 2025 ######
                        elif estado_solicitud == '4':
                                download_pending = True
                                numero_cfdis = 0.0
                                number_of_documents = numero_cfdis ### Total Descargado en el SAT
                                _logger.info('\n################ Solicitud con Errores, ya no se podra descarga. Crea una nueva solicitud pero cambia el periodo (fechas) de la misma ( %s ).....' % rec.name)
                                status_solicitud = status_solicitud+", SAT - preparando archivo."
                                no_data = True
                        elif estado_solicitud == '5':
                                download_pending = True
                                numero_cfdis = 0.0
                                number_of_documents = numero_cfdis ### Total Descargado en el SAT
                                _logger.info('\n################ Solicitud Rechazada, ya no se podra descarga. Crea una nueva solicitud pero cambia el periodo (fechas) de la misma ( %s ).....' % rec.name)
                                status_solicitud = status_solicitud+", SAT - preparando archivo."
                                no_data = True
                        elif estado_solicitud == '6':
                                download_pending = True
                                numero_cfdis = 0.0
                                number_of_documents = numero_cfdis ### Total Descargado en el SAT
                                _logger.info('\n################ Solicitud Vencida, ya no se podra descarga. Crea una nueva solicitud pero cambia el periodo (fechas) de la misma ( %s ).....' % rec.name)
                                status_solicitud = status_solicitud+", SAT - preparando archivo."
                                no_data = True
                        # --- # 
                        else:
                            download_pending = False
                            status_solicitud = 'No se encontró la información'
                            no_data = True
                    ### Eliminando los Temporales
                    #self.clean_tmp_data(file_globals, [zip_pth])

                # {'estado_solicitud': '3', 'numero_cfdis': '8', 'cod_estatus': '5000', 'paquetes': ['a4897f62-a279-4f52-bc35-03bde4081627_01'], 'codigo_estado_solicitud': '5000', 'mensaje': 'Solicitud Aceptada'}

            ### Actualizamos los Valores para crear el registro de tablero ###
            periodo_trunco = str(rec.date_start)[0:10]+' - '+str(rec.date_stop)[0:10]

            vals = {
                     'name': rec.name,
                     'date': fields.Date.today(),
                     'user_id': user_id,
                     'number_of_documents': number_of_documents,
                     'number_of_invoices': number_of_invoices,
                     'number_of_nc_invoices': number_of_nc_invoices,
                     'number_of_supplier_inv': number_of_supplier_inv,
                     'number_of_nc_supplier_inv': number_of_nc_supplier_inv,
                     'number_of_payments': number_of_payments,
                     'periodo': periodo_trunco,
                     'datas_fname':datas_fname,
                     'file':paquete_b64,
                     'download_file': True,
                     'download_type': rec.download_type,
                     'id_solicitud': id_solicitud,
                     'status_solicitud': status_solicitud,
                     'color': 9 if cod_estatus != '5000' else 10,
                     'download_pending': download_pending,
                     'no_data': no_data,
                     'date_start': rec.date_start,
                     'date_stop': rec.date_stop,
                     'package_pending': package_pending,
                     'company_id': self.company_id.id if self.company_id else False,
            }
            if file_ready_for_download:
                ### Si el Archivo se Descargo al mismo tiempo entonces marcamos otro color ###
                vals.update({'color': 11,'is_favorite': False})
            manager_download_obj = self.env['cfdi.account.dashboard.manager']
            manager_br = manager_download_obj.create(vals)
            if file_ready_for_download or cod_estatus != '5000':
                manager_br.write({'sequence': manager_br.id})
            if not file_ready_for_download:
                manager_br.write({'sequence': 100+manager_br.id})
            ### Retornamos el Resultado ###
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            file_url = base_url+"/web/content?model=cfdi.account.dashboard.manager&field=file&filename_field=datas_fname&id=%s&&download=true" % (manager_br.id,)
            
            return {
                        'name': 'Resultado de Consutla SAT',
                        'view_mode': 'form',
                        'view_id': self.env.ref('l10n_mx_auditor_sat.cfdi_account_dashboard_manager_form').id,
                        'res_model': 'cfdi.account.dashboard.manager',
                        'context': "{}", # self.env.context
                        'type': 'ir.actions.act_window',
                        'res_id': manager_br.id,
                    }
                    
            # if no_data == False:
            #     manager_br.compute_documents_from_period()
            #     return {
            #             'type': 'ir.actions.act_url',
            #             'url': file_url,
            #             'target': 'new'
            #         }
            # else:
            #     return {
            #                 'name': 'Resultado de Consutla SAT',
            #                 'view_mode': 'form',
            #                 'view_id': self.env.ref('l10n_mx_auditor_sat.cfdi_account_dashboard_manager_form').id,
            #                 'res_model': 'cfdi.account.dashboard.manager',
            #                 'context': "{}", # self.env.context
            #                 'type': 'ir.actions.act_window',
            #                 'res_id': manager_br.id,
            #             }
                        

    def constraint_unique_request(self, date_start, date_stop):
        dashboard_obj = self.env['cfdi.account.dashboard.manager']
        dashboard_previous_ids = dashboard_obj.search([('date_start','=',date_start),
                                                       ('date_stop','=',date_stop),
                                                       ('download_pending','=',False)])
        return dashboard_previous_ids


    
    def clean_tmp_data(self, file_globals, extra_data=[]):
        _logger.info("\n:::::::::::::::::::::::::: Comenzando la Eliminacion de los Temporales")
        temporary_path_files = file_globals['temporary_path_files']
        if extra_data:
            temporary_path_files.extend(extra_data)
        _logger.info("\n:::::::::::::::::::::::::: temporary_path_files %s" % temporary_path_files )
        ### Eliminando Temporales de Dispersion ###
        for file_tmp in temporary_path_files:
            os.unlink(file_tmp)
        return True

    # ### Librerias Alternativas ####
    # 
    # def get_download_request(self, file_globals, download_type='emitidos'):
    #     for rec in self:
    #         company_user = self.env.user.company_id
    #         fecha_inicial = rec.date_start
    #         fecha_final = rec.date_stop
    #         print ("#### fecha_inicial >>> ",fecha_inicial)
    #         print ("#### fecha_final >>> ",fecha_final)
    #         rfc_emisor = company_user.vat
    #         rfc_receptor = company_user.vat
    #         fname_key = file_globals['fname_key'] ### Key PEM
    #         FIEL_PAS = file_globals['password']
    #         cer_der = file_globals['cer_der']
    #         key_der = file_globals['key_der']
    #         fiel = Fiel(cer_der, key_der, FIEL_PAS)

    #         fname_key_b64 = open(fname_key, 'rb').read()

    #         login = Login.TokenRequest()
    #         token = login.soapRequest(cer_der, fname_key_b64)
    #         print ("### TOKEN >>> ",token)
    #         descarga = Request.RequestDownloadRequest()
    #         descarga_res = descarga.soapRequest(cer_der, fname_key_b64, token, fecha_inicial, fecha_final,
    #                         'CFDI', {'rfc_emisor': rfc_emisor, 'rfc_receptor': rfc_receptor})

    #         print ("########## descarga_res >>>> ",descarga_res)


# from cfdiclient import Autenticacion
# from cfdiclient import Fiel

# FIEL_KEY = '/tmp/argil.key'
# FIEL_CER = '/tmp/argil.cer'
# FIEL_PAS = '4h0l1b4m4'
# cer_der = open(FIEL_CER, 'rb').read()
# key_der = open(FIEL_KEY, 'rb').read()

# fiel = Fiel(cer_der, key_der, FIEL_PAS)

# auth = Autenticacion(fiel)

# token = auth.obtener_token()

# print(token)

