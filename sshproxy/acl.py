#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 aoû 08, 11:34:44 by david
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

import time, datetime

from registry import Registry
import log
from aclparser import ACLRuleParser
from util import OrderedDict

class ACLRule(Registry):
    _class_id = 'ACLRule'

    def __reginit__(self, name, rule):
        self.name = name
        self.rule = rule
        self.parser = ACLRuleParser()

    def eval(self, namespace):
        self.parser.namespace = namespace
        return self.parser.eval(self.rule)

ACLRule.register()

class ProxyNamespace(Registry, dict):
    _class_id = 'ProxyNamespace'
    def __reginit__(self, default_namespace=None, **kw):
        self.defaults = default_namespace or {}
        dict.__init__(self, **kw)

    def get(self, tag, default=None):
        if hasattr(self, 'dot_'+tag):
            return getattr(self, 'dot_'+tag)()
        else:
            return self.defaults.get(tag, default)

    def __getitem__(self, tag):
        if hasattr(self, 'dot_'+tag):
            return getattr(self, 'dot_'+tag)()
        raise AttributeError('proxy does not have such element: %s' % tag)

    def dot_time(self):
        return str(datetime.datetime.now().strftime("%H:%M"))

    def dot_date(self):
        return str(datetime.datetime.now().strftime("%Y-%m-%d"))

    def dot_datetime(self):
        return str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    def dot_doy(self):
        return datetime.datetime.now().strftime("%j")

    def dot_week(self):
        return str(datetime.datetime.now().strftime("%W"))

    def dot_unixtime(self):
        return int(time.time())

    def dot_dow(self):
        return str(datetime.datetime.now().strftime("%w"))

ProxyNamespace.register()




class ACLTags(Registry):
    _class_id = 'ACLTags'

    def __reginit__(self, tags=None, obj=None):
        self.tags = {}
        if tags:
            self.add_tags(tags)
        if obj:
            self.add_attributes(obj)

    def add_tag(self, tag, value):
        if tag[:4] == 'acl.':
            tag = tag[4:]
            value = ACLRule(tag, value)
        else:
            value = str(value or '')
        self.tags[str(tag)] = value

    def add_tags(self, tags):
        for tag, value in tags.items():
            self.add_tag(tag, value)

    def add_attributes(self, obj):
        for tag, value in [ (k, getattr(obj, k)) for k in dir(obj) ]:
            if tag[0] != '_' and isinstance(value, str):
                self.add_tag(tag, value)

    def update(self, other):
        if not other or not other.tags.keys():
            return
        self.tags.update(other.tags)

    def __getattr__(self, tag):
        return self.tags[str(tag)]

    def __getitem__(self, tag):
        return self.tags[str(tag)]

    def __delitem__(self, tag):
        del self.tags[str(tag)]

    def get(self, tag, default=None):
        return self.tags.get(tag, default)

    def has_key(self, tag):
        return self.tags.has_key(str(tag))

    def keys(self):
        return self.tags.keys()

    def items(self):
        return self.tags.items()

    def __str__(self):
        return repr(self.tags)

    __repr__ = __str__

ACLTags.register()

class ACList(list):
    pass

class ACLDB(Registry):
    _class_id = 'ACLDB'
    _singleton = True
    
    def __reginit__(self):
        self.rules = OrderedDict()
        self.load_rules()

    def load_rules(self):
        pass

    def save_rules(self):
        pass

    def add_rule(self, acl, rule=None, index=None):
        if rule is None:
            rule = ACLRule(acl, 'False')
        elif not isinstance(rule, ACLRule):
            rule = ACLRule(acl, str(rule))

        if not self.rules.get(acl, None):
            self.rules[acl] = ACList()

        if index is None:
            self.rules[acl].append(rule)
            return len(self.rules[acl]) - 1
        else:
            self.rules[acl].insert(index, rule)
            return index

    def set_rule(self, acl, rule, index):
        if not self.rules.get(acl, None):
            return False

        try:
            self.rules[acl][index].rule = str(rule)
            return True
        except IndexError:
            return False

    def del_rule(self, acl, index):
        if not self.rules.get(acl, None):
            return False

        if index is None:
            while len(self.rules[acl]):
                self.del_rule(acl, 0)
            return True
        else:
            try:
                del self.rules[acl][index]
            except IndexError:
                return False

        if not len(self.rules[acl]):
            del self.rules[acl]
        return True

    def list_rules(self, name=None):
        aclrules = ACList()
        for rulename in self.rules.keys():
            for rule in self.rules[rulename]:
                if name in (None, rulename):
                    aclrules.append(rule)
        return aclrules


    def check(self, acl, **namespaces):
        try:
            namespace = dict(self.rules)
            for ns in namespaces:
                if not namespace.has_key(ns):
                    namespace[ns] = ACLTags()
                namespace[ns].update(namespaces[ns])

            result = None
            match = ''

            if isinstance(acl, ACLRule):
                match = repr(acl.rule)
                result = acl.eval(namespace)
            else:
                for rulename in self.rules.keys():
                    for rule in self.rules[rulename]:
                        if rulename == acl:
                            match = repr(rule.rule)
                            if rule.eval(namespace):
                                result = True
                                break
                            else:
                                result = False
    
            if result is None:
                result = False
                log.info('ACL %s not found' % acl)
            else:
                log.info('ACL %s %s %s' % (acl, result, match))
                pass
            return result
        except:
            log.error('Error while checking ACL %s' % acl)
            raise


ACLDB.register()


