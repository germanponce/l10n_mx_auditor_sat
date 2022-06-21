# -*- encoding: utf-8 -*-

##############################################################################
{
    "name" : "Mexico - Suite para Auditoria CFDI vs SAT",
    'version': '1',
    "author" : "Argil Consulting",
    "category" : "SAT",
    'description': """

Con este módulo puede realizar lo siguiente:
* Solicitar al portal del SAT la generación del archivo ZIP de los CFDIs de un periodo en particular
* Se revisa de manera periódica para ver si el archivo ZIP ya se encuentra disponible en el portal del SAT y se hace la descarga    
    """,
    "website" : "http://www.argil.mx",
    "license" : "AGPL-3",
    "depends" : [
                    "account",
                    'base_setup', 
                    'product', 
                    'portal', 
                ],
    "external_dependencies": {
                    "python" : ["cfdiclient", "suds-jurko"]
                    },
    "init_xml" : [],
    "demo_xml" : [],
    "data" : [
                    'security/security_group.xml',
                    'security/ir.model.access.csv',
                    'data/data_cron.xml',
                    'views/res_config_view.xml',
                    'views/dashboard.xml',
                    'views/account.xml',
                    ],
    "installable" : True,
}
