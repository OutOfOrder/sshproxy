#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Michal Mazurek; WALLIX, SARL. <michal.mazurek at wallix dot com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

__plugin_name__ = "Email Notifier"
__description__ = """
    Send exceptional failures to the site administrator
    by mail.
"""


def __init_plugin__():
    from notifier import EmailNotifierServer
    EmailNotifierServer.register()
    

def __setup__():
    from sshproxy import menu
    from sshproxy.config import get_config
    from sshproxy.util import istrue
    import notifier
    
    cfg = get_config('email_notifier')
    items = []

    def update_admin_email(value):
        cfg['admin_email'] = value
    def update_smtp_server(value):
        cfg['smtp_server'] = value
    def update_smtp_port(value):
        cfg['smtp_port'] = value
    def update_smtp_tls(value):
        if istrue(value):
            cfg['smtp_tls'] = 'yes'
        else:
            cfg['smtp_tls'] = 'no'
    def update_smtp_login(value):
        cfg['smtp_login'] = value
    def update_smtp_password(value):
        cfg['smtp_password'] = value
    def update_smtp_sender(value):
        cfg['smtp_sender'] = value
                
        
    items.append(menu.MenuInput("Email used for notifications.",
                "",
                cfg.get('admin_email', raw=True),
                cb=update_admin_email))
    items.append(menu.MenuInput("Sender email.",
                "",
                cfg.get('smtp_sender', raw=True),
                cb=update_smtp_password))
    items.append(menu.MenuInput("SMTP Server IP address.",
                "",
                cfg.get('smtp_server', raw=True),
                cb=update_smtp_server))
    items.append(menu.MenuInput("SMTP Server port (default 25).",
                "25",
                cfg.get('smtp_port', raw=True),
                cb=update_smtp_port))
    items.append(menu.MenuInput("Use TLS for SMTP connection [yes/no].",
                "",
                cfg.get('smtp_tls', raw=True),
                cb=update_smtp_tls))
    items.append(menu.MenuInput("SMTP login, leave empty if not used.",
                "",
                cfg.get('smtp_login', raw=True),
                cb=update_smtp_login))
    items.append(menu.MenuInput("SMTP password, leave empty if not used.",
                "",
                cfg.get('smtp_password', raw=True),
                cb=update_smtp_password))
    
    return items
        
        
