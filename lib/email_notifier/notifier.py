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

import smtplib
import types
import socket, os
from sshproxy.config import get_config, ConfigSection
from sshproxy.util import istrue
from sshproxy import log

message_template = """
Reported error: %(reason)s
Client: %(client)s
Site: %(site)s
Connection Type: %(conntype)s
Date: %(when)s
Additional message:
%(msg)s

--
Your sshproxy <%(sshproxy_id)s>
"""


class EmailNotifierConfigSection(ConfigSection):
    section_id = 'email_notifier'
    section_defaults = {
        'admin_email': '',
        'smtp_server': 'localhost',
        'smtp_port': '25',
        'smtp_login': '',
        'smtp_password': '',
        'smtp_sender': '%s@%s' % (os.environ['USER'], socket.getfqdn()),
        'smtp_tls': 'no',
        'message_template': message_template.replace('%', '%%'),
        }
    types = {
        'smtp_port': int,
        }

EmailNotifierConfigSection.register()



class Email(object):
    """Class for sending emails using smtplib"""
    
    recipients = []
    
    def __init__(self, server, port=25, login="", password="", tls=False):
        """Constructor
        
        Email(server, [port, [login, [password]], tls])
        
        @param server: smtp server address
        @param port: smtp port number
        @param login: auth username (optional)
        @param password: auth password (optional)
        @param tls: use TLS (defaults to False)
        """
        self.smtp_server = server
        self.smtp_port = port
        self.smtp_tls = tls
        self.login = login
        self.password = password

    def new(self, recipients=None, sender=None, subject=None, msg=None):
        """Creating new email
        
        @param recipient: string or iterable object containing string
        @param sender: string with sender address
        @param subject: subject of message
        @param msg: message body
        """
        try:
            if types.StringType == type(recipients):
                recipients = [recipients]
                
            for recipient in recipients:
                self.recipients.append(recipient)
        except TypeError:
            raise TypError, "'recipients' is not iterable, nor a string"
        
        self.sender = sender
        self.subject = subject
        self.msg = msg
        
    def _connect_to_smtp(self):
        """Connecting to smtp server, this methods runs also self._authorize()"""
        self._connection = smtplib.SMTP(self.smtp_server, self.smtp_port)
        self._starttls()
        self._authorize()
        
        
    def _starttls(self):
        """If TLS is requested, try to put the connection in TLS mode."""
        if self.smtp_tls:
            self._connection.starttls()

    def _authorize(self):
        """If there are give login and password, it tries to authorize on
        smtp server"""
        if self.login and self.password:
            self._connection.login(self.login, self.password)

    def send_email(self):
        """Method which sends email, if there are any problems it raises
        smtplib.SMTPException"""
        
        msg = ""
        msg += "From: %s\n" % self.sender
        msg += "To: %s\n" % ", ".join(self.recipients)
        msg += "Subject: %s\n\n%s" % (self.subject, self.msg)
        try:
            self._connect_to_smtp()
        except (socket.error, socket.herror):
            return False
        result = self._connection.sendmail(self.sender, self.recipients, msg)
        if result:
            errmsg = ""
            for recp in result.keys():
                errmsg += """Server returned error for recipient: %s
                
                %s
                %s
                """ % (recp, result[recp][0], result[recp][1])
            
            raise smtplib.SMTPException, errmsg
        
        self._connection.quit()
        
        return True
        

from sshproxy.registry import get_class

Server = get_class("Server")

class EmailNotifierServer(Server):

    def do_work(self):
        self.get_site_name()
        Server.do_work(self)
    
    def get_site_name(self):
        """getting the site name"""
        if len(self.args) == 0:
            self.g_site = "Console Session"
            self.g_conn_type = "scp"
        else:
            if self.args[0] == "scp":
                self.g_conn_type = "scp"
                argv = self.args[1:]
                while True:
                    if argv[0][0] == '-':
                        argv.pop(0)
                        continue
                    break
                
                self.g_site = argv[0].split(":", 1)[0]
            elif self.args[0][0] != '-':
                
                if len(self.args) > 1:
                    self.g_conn_type = "remote_exec"
                else:
                    self.g_conn_type = "shell"
                self.g_site = self.args[0]
            else:
                self.g_site = "proxy_command"
        return self.g_site
    
    def report_failure(self, reason, *args, **kwargs):
        """Reporting error
        
        @param reason: reason of failure"""
        from datetime import datetime

        cfg = get_config('email_notifier')

        tpldict = {}
        
        tpldict['reason'] = reason
        if len(args) > 0:
            tpldict['msg'] = args[0]
        else:
            tpldict['msg'] = "No additional message."
        
        
        tpldict['client'] = self.username
        tpldict['site'] = self.g_site
        tpldict['when'] = datetime.now()
        tpldict['conntype'] = self.g_conn_type
        tpldict['sshproxy_id'] = cfg['smtp_sender'] # ?


        server = cfg['smtp_server']
        try:
            port = cfg['smtp_port']
        except ValueError:
            port = 25
            
        login = cfg['smtp_login']
        password = cfg['smtp_password']
        
        admin_email = cfg['admin_email']
        sender = cfg['smtp_sender']

        tls = istrue(cfg["smtp_tls"])
        
        msg = cfg['message_template'] % tpldict

        if admin_email != "" and "@" in admin_email:
            email = Email(server, port, login, password, tls=tls)
            
            email.new(admin_email, sender, "Failure Report", msg)
            
            try:
                email.send_email()
            except smtplib.SMTPException, e:
                log.exception(e)
        Server.report_failure(self, reason, *args, **kwargs)


