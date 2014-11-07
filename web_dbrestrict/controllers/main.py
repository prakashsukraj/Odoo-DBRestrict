# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


# -*- coding: utf-8 -*-

import jinja2
import os
import simplejson
import sys
import openerp
import openerp.modules.registry
from openerp.tools import topological_sort
from openerp import http
from openerp.http import request, serialize_exception as _serialize_exception

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('openerp.addons.web', "views")

env = jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = simplejson.dumps

db_monodb = http.db_monodb

def module_installed_bypass_session(dbname):
    loadable = http.addons_manifest.keys()
    modules = {}
    try:
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            m = registry.get('ir.module.module')
            # TODO The following code should move to ir.module.module.list_installed_modules()
            domain = [('state','=','installed'), ('name','in', loadable)]
            ids = m.search(cr, 1, [('state','=','installed'), ('name','in', loadable)])
            for module in m.read(cr, 1, ids, ['name', 'dependencies_id']):
                modules[module['name']] = []
                deps = module.get('dependencies_id')
                if deps:
                    deps_read = registry.get('ir.module.module.dependency').read(cr, 1, deps, ['name'])
                    dependencies = [i['name'] for i in deps_read]
                    modules[module['name']] = dependencies
    except Exception,e:
        pass
    sorted_modules = topological_sort(modules)
    return sorted_modules
	
def module_boot(db=None):
    server_wide_modules = openerp.conf.server_wide_modules or ['web']
    serverside = []
    dbside = []
    for i in server_wide_modules:
        if i in http.addons_manifest:
            serverside.append(i)
    monodb = db or db_monodb()
    if monodb:
        dbside = module_installed_bypass_session(monodb)
        dbside = [i for i in dbside if i not in serverside]
    addons = serverside + dbside
    return addons
	
class Database_Password(openerp.addons.web.controllers.main.Database):

    @http.route('/web/database/manager', type='http', auth="none")
    def manager(self, **kw):
        request.session.logout()
        return http.local_redirect('/web/password')

    @http.route('/web/password', type='http', auth='public', website=True)
    def pasword(self, redirect=None, **post):	
        return request.render('web_dbrestrict.dbmanager_password', {'url_root': request.httprequest.url_root})
                
    @http.route('/web/dbmanager_password', type='http', auth='public', website=True)
    def dbmanager_password(self, cert_type=None, **post):
        password = request.params['password']	
        if password == 'Your_Password':
            return env.get_template("database_manager.html").render({
                'modules': simplejson.dumps(module_boot()),
            })	
        else:
            values = request.params.copy()		
            values['error'] = "Wrong password"				
            return request.render('web_dbrestrict.dbmanager_password', values)		
        
        
    
