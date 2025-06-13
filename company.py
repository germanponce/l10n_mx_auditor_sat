# -*- encoding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from pytz import timezone
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import base64
import ssl
from OpenSSL import crypto
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit ='res.company'

    certificate_file = fields.Binary(string='Certificado (*.cer)',
                    filters='*.cer,*.certificate,*.cert', 
                    help='Seleccione el archivo del Certificado de Sello Digital (CSD). Archivo con extensión .cer')
    certificate_key_file = fields.Binary(string='Llave del Certificado (*.key)',
                    filters='*.key', 
                    help='Seleccione el archivo de la Llave del Certificado de Sello Digital (CSD). Archivo con extensión .key')
    certificate_password = fields.Char(string='Contraseña Certificado', size=64,
                    invisible=False, 
                    help='Especifique la contraseña de su CSD')
    certificate_file_pem = fields.Binary(string='Certificado (PEM)',
                    filters='*.pem,*.cer,*.certificate,*.cert', 
                    help='Este archivo es generado a partir del CSD (.cer)')
    certificate_key_file_pem = fields.Binary(string='Llave del Certificado (PEM)',
                    filters='*.pem,*.key', help='Este archivo es generado a partir del CSD (.key)')
    certificate_pfx_file = fields.Binary(string='Certificado (PFX)',
                    filters='*.pfx', help='Este archivo es generado a partir del CSD (.cer)')
    fiel_date_start  = fields.Date(string='Vigencia de', help='Fecha de inicio de vigencia del CSD')
    fiel_date_end    = fields.Date(string='Vigencia hasta',  help='Fecha de fin de vigencia del CSD')
    fiel_serial_number = fields.Char(string='Número de Serie', size=64, 
                                help='Number of serie of the certificate')
    fname_xslt  = fields.Char('Path Parser (.xslt)', size=256, 
                             help='Directorio donde encontrar los archivos XSLT. Dejar vacío para que se usen las opciones por defecto')
    
    download_automatically = fields.Boolean('Consultar Descargas Aut.',
                                            help='Permite consultar los paquetes pendientes de forma automatica, se puede programar el tiempo de ejecucion.', )
    
    
    # @api.onchange('certificate_password')
    # def _onchange_certificate_password(self):
    #     warning = {}
    #     certificate_lib = self.env['facturae.certificate.library']
    #     certificate_file_pem = False
    #     certificate_key_file_pem = False
    #     cer_der_b64str  = self.certificate_file and str.encode(self.certificate_file) or False
    #     key_der_b64str  = self.certificate_key_file and str.encode(self.certificate_key_file) or False
    #     password        = self.certificate_password or False        
    #     if cer_der_b64str and key_der_b64str and password:
    #         if True:
    #             cer_pem_b64 = ssl.DER_cert_to_PEM_cert(base64.decodestring(str.encode(self.certificate_file))).encode('UTF-8')
    #             key_pem_b64 = certificate_lib.convert_key_cer_to_pem(base64.decodestring(str.encode(self.certificate_key_file)),
    #                                                                 str.encode(self.certificate_password))
    #             if not key_pem_b64:
    #                 key_pem_b64 = certificate_lib.convert_key_cer_to_pem(base64.decodestring(str.encode(self.certificate_key_file)),
    #                                                                 str.encode(self.certificate_password+ ' '))
    #             pfx_pem_b64 = certificate_lib.convert_cer_to_pfx(cer_pem_b64, key_pem_b64,
    #                                                              self.certificate_password)
    #             cert = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem_b64)
    #             x = hex(cert.get_serial_number())
    #             self.fiel_serial_number = x[1::2].replace('x','')
    #             date_start = cert.get_notBefore().decode("utf-8") 
    #             date_end = cert.get_notAfter().decode("utf-8") 
    #             self.fiel_date_start = date_start[:4] + '-' + date_start[4:][:2] + '-' + date_start[6:][:2]
    #             self.fiel_date_end = date_end[:4] + '-' + date_end[4:][:2] + '-' + date_end[6:][:2]
    #             self.certificate_file_pem       = base64.b64encode(cer_pem_b64)
    #             self.certificate_key_file_pem   = base64.b64encode(key_pem_b64)
    #             self.certificate_pfx_file       = base64.b64encode(pfx_pem_b64)
    #         else:
    #             warning = {
    #                 'title': _('Advertencia!'),
    #                 'message': _('El archivo del Certificado, la Llave o la Contraseña son incorrectas o no están definidas.\nPor favor revise')
    #             }
    #             self.certificate_file_pem = False,
    #             self.certificate_key_file_pem = False,
    #             self.certificate_pfx_file = False,
                
    #     else:
    #             warning = {
    #                 'title': _('Advertencia!'),
    #                 'message': _('Falta algún dato, revise que tenga el Certificado, la Llave y la contraseña correspondiente')
    #             }
    #     return {'warning': warning}



class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    

    certificate_file = fields.Binary(string='Certificado (*.cer)',
                    filters='*.cer,*.certificate,*.cert', 
                    help='Seleccione el archivo del Certificado de Sello Digital (CSD). Archivo con extensión .cer', 
                    related="company_id.certificate_file", readonly=False)
    certificate_key_file = fields.Binary(string='Llave del Certificado (*.key)',
                    filters='*.key', 
                    help='Seleccione el archivo de la Llave del Certificado de Sello Digital (CSD). Archivo con extensión .key',
                    related="company_id.certificate_key_file", readonly=False)
    certificate_password = fields.Char(string='Contraseña', size=64,
                    invisible=False, 
                    help='Especifique la contraseña de su CSD',
                    related="company_id.certificate_password", readonly=False)
    certificate_file_pem = fields.Binary(string='Certificado (PEM)',
                    filters='*.pem,*.cer,*.certificate,*.cert', 
                    help='Este archivo es generado a partir del CSD (.cer)',
                    related="company_id.certificate_file_pem", readonly=False)
    certificate_key_file_pem = fields.Binary(string='Llave del Certificado (PEM)',
                    filters='*.pem,*.key', help='Este archivo es generado a partir del CSD (.key)',
                    related="company_id.certificate_key_file_pem", readonly=False)
    certificate_pfx_file = fields.Binary(string='Certificado (PFX)',
                    filters='*.pfx', help='Este archivo es generado a partir del CSD (.cer)',
                    related="company_id.certificate_pfx_file", readonly=False)
    fiel_date_start  = fields.Date(string='Vigencia de', help='Fecha de inicio de vigencia del CSD',
                    related="company_id.fiel_date_start", readonly=False)
    fiel_date_end    = fields.Date(string='Vigencia a',  help='Fecha de fin de vigencia del CSD',
                    related="company_id.fiel_date_end", readonly=False)
    fiel_serial_number = fields.Char(string='Número de Serie', size=64, 
                                help='Number of serie of the certificate',
                                related="company_id.fiel_serial_number", readonly=False)
    download_automatically = fields.Boolean('Consulta (Automatica)',
                                            related="company_id.download_automatically",
                                            readonly=False,
                                            help='Permite consultar los paquetes pendientes de forma automatica, se puede programar el tiempo de ejecucion.', )
    
    

    @api.onchange('certificate_password')
    def _onchange_certificate_password(self):
        warning = {}
        certificate_lib = self.env['facturae.certificate.library']
        certificate_file_pem = False
        certificate_key_file_pem = False
        error_in_decode = False
        try:
            cer_der_b64str  = self.certificate_file and str.encode(self.certificate_file) or False
            key_der_b64str  = self.certificate_key_file and str.encode(self.certificate_key_file) or False
            password        = self.certificate_password or False  
        except:
            error_in_decode = True
        if error_in_decode:
            return {}      
        if cer_der_b64str and key_der_b64str and password:
            if True:
                cer_pem_b64 = ssl.DER_cert_to_PEM_cert(base64.decodestring(str.encode(self.certificate_file))).encode('UTF-8')
                key_pem_b64 = certificate_lib.convert_key_cer_to_pem(base64.decodestring(str.encode(self.certificate_key_file)),
                                                                    str.encode(self.certificate_password))
                if not key_pem_b64:
                    key_pem_b64 = certificate_lib.convert_key_cer_to_pem(base64.decodestring(str.encode(self.certificate_key_file)),
                                                                    str.encode(self.certificate_password+ ' '))
                pfx_pem_b64 = certificate_lib.convert_cer_to_pfx(cer_pem_b64, key_pem_b64,
                                                                 self.certificate_password)
                cert = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem_b64)
                x = hex(cert.get_serial_number())
                self.fiel_serial_number = x[1::2].replace('x','')
                date_start = cert.get_notBefore().decode("utf-8") 
                date_end = cert.get_notAfter().decode("utf-8") 
                self.fiel_date_start = date_start[:4] + '-' + date_start[4:][:2] + '-' + date_start[6:][:2]
                self.fiel_date_end = date_end[:4] + '-' + date_end[4:][:2] + '-' + date_end[6:][:2]
                self.certificate_file_pem       = base64.b64encode(cer_pem_b64)
                self.certificate_key_file_pem   = base64.b64encode(key_pem_b64)
                self.certificate_pfx_file       = base64.b64encode(pfx_pem_b64)
            else:
                warning = {
                    'title': _('Advertencia!'),
                    'message': _('El archivo del Certificado, la Llave o la Contraseña son incorrectas o no están definidas.\nPor favor revise')
                }
                self.certificate_file_pem = False,
                self.certificate_key_file_pem = False,
                self.certificate_pfx_file = False,
                
        else:
            return {}
        return {'warning': warning}