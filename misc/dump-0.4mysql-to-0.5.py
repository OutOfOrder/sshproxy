#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Aug 12, 01:28:00 by david
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

import sys, os
from optparse import OptionParser, _

import MySQLdb



parser = OptionParser()

parser.remove_option('-h')

parser.add_option("", "--help", action="help",
                    help=_("show this help message and exit"))

parser.add_option("-h", "--host", dest="host", default="localhost",
                    help="Connect to host.",
                    metavar="HOST")

parser.add_option("-u", "--user", dest="user",
                    help="User login if not current user.",
                    metavar="USER")

parser.add_option("-p", "--password", dest="password", default='',
                    help="Password to use when connecting to server. If password is not given it's asked from the tty.",
                    metavar="PASSWORD")

parser.add_option("-P", "--port", dest="port", default=3306,
                    help="Port number to use for connection",
                    metavar="PORT")

parser.add_option("-D", "--database", dest="database", default='sshproxy',
                    help="Database to use.",
                    metavar="DATABASE")

(options, args) = parser.parse_args()

# mandatory arguments:
mandargs = ('user', 'database', 'host', 'port')

for opt in mandargs:
    if not getattr(options, opt, None):
        print "Option %s is mandatory" % opt
        sys.exit(1)

try:
    options.port = int(options.port)
    (0 < options.port < 65536) or int('Not a valid value')
except ValueError:
    print "Port must be numeric and comprised between 1 and 65535"
    sys.exit(1)


db = MySQLdb.connect(host=options.host,
                     port=int(options.port),
                     db=options.database,
                     user=options.user,
                     passwd=options.password)

def q(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace("\n", "\\n")

def sql_get(query):
    sql = db.cursor()
    sql.execute(query)
    result = sql.fetchone()
    sql.close()
    if not result or not len(result):
        return None
    if len(result) == 1:
        return result[0]
    return result

def sql_list(query):
    sql = db.cursor()
    sql.execute(query)
    for result in sql.fetchall():
        yield result
    sql.close()
    return






p_u = {}
s_d = {}
r_d = {}
profiles = {}

domain_sites = list(sql_list("select d.name, s.name from domain as d, domain_site as ds, site as s where d.id = ds.domain_id and ds.site_id = s.id"))
for domain, site in domain_sites:
    if not s_d.has_key(site):
        s_d[site] = [ domain ]
    else:
        s_d[site].append(domain)
    
sites = list(sql_list("select * from site"))
for id, name, ip_address, port, location in sites:
    print '''add_site %s''' % name
    print '''tag_site %s ip_address=%s port=%s location="%s" domains="%s"''' % (name, ip_address, port, q(location), q(' '.join(s_d.get(name, []))))

print

domain_rlogins = list(sql_list("select d.name, r.uid, s.name from domain as d, domain_rlogin as dr, rlogin as r, site as s where d.id = dr.domain_id and dr.rlogin_id = r.id and r.site_id = s.id"))
for domain, rlogin, name in domain_rlogins:
    site = '%s@%s' % (rlogin, name)
    if not r_d.has_key(site):
        r_d[site] = [ domain ]
    else:
        r_d[site].append(domain)
    
rlogins = list(sql_list("select uid, password, priority, name from rlogin, site where rlogin.site_id = site.id"))
for uid, password, priority, name in rlogins:
    print '''add_site %s@%s''' % (uid, name)
    print '''tag_site %s@%s password="%s" priority=%s''' % (uid, name, q(password), priority),
    if len(r_d.keys()):
        print '''domains="%s"''' % q(' '.join(r_d.get('%s@%s' % (uid, name), []))),
    print
print

profile_domain = list(sql_list("select p.name, d.name from profile as p, profile_domain as pd, domain as d where p.id = pd.profile_id and pd.domain_id = d.id"))
for profile, domain in profile_domain:
    profiles[profile] = profile
    print '''set_aclrule connect "%s" in split(client.profiles) and "%s" in split(site.domains)''' % (q(profile), q(domain))

print "set_aclrule authenticate:0 True"
print "set_aclrule authorize:0 True"
print "set_aclrule shell_session True"
print "set_aclrule remote_exec True"
print "set_aclrule scp_transfer True"

print

user_profiles = list(sql_list("select l.uid, p.name from login as l, login_profile as lp, profile as p where l.id = lp.login_id and lp.profile_id = p.id"))
for username, profile in user_profiles:
    profiles[profile] = profile
    if not p_u.has_key(username):
        p_u[username] = [ profile ]
    else:
        p_u[username].append(profile)

users = list(sql_list("select * from login"))
for id, username, password, pkey in users:
    print '''add_client %s''' % username
    print '''tag_client %s password="%s" pkey="%s" profiles="%s"''' % (username, q(password), q(pkey), q(' '.join(p_u.get(username, []))))


