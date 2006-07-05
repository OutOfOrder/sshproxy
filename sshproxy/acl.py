#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 05, 03:40:15 by david
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

from registry import Registry

class ACLTags(Registry):
    def __init__(self, tags=None, obj=None):
        self.tags = {}
        if tags:
            self.add_tags(tags)
        if obj:
            self.add_attributes(obj)

    def add_tag(self, tag, value):
        self.tags[tag] = value

    def add_tags(self, tags):
        for tag, value in tags.items():
            self.tags[tag] = value

    def add_attributes(self, obj):
        for tag, value in dir(obj):
            if tag[0] != '_' and isinstance(value, str):
                self.tags[tag] = value

class Operator(object):
    _ops = {}
    def __init__(self, left, right):
        self.right = right
        self.left = left

    @staticmethod
    def add(cls):
        Operator._ops[cls.token] = cls

    @staticmethod
    def get(op):
        if op in Operator._ops:
            return Operator._ops[op]
        return None

    def __str__(self):
        return '%s %s %s' % (repr(self.left), self.token, repr(self.right))

    def __repr__(self):
        return '%s %s %s' % (repr(self.left), self.token, repr(self.right))

class Equals(Operator):
    token = '='
    p = 0
    def op(self):
        return self.left == self.right

class Different(Operator):
    token = '!='
    p = 0
    def op(self):
        return self.left == self.right

class Superior(Operator):
    token = '>'
    p = 0
    def op(self):
        return self.left > self.right

class Inferior(Operator):
    token = '<'
    p = 0
    def op(self):
        return self.left < self.right

class SuperiorEq(Operator):
    token = '>='
    p = 0
    def op(self):
        return self.left >= self.right

class InferiorEq(Operator):
    token = '<='
    p = 0
    def op(self):
        return self.left <= self.right

class Not(Operator):
    token = 'not'
    p = 1
    def op(self):
        return not self.right

class In(Operator):
    token = 'in'
    p = 0
    def op(self):
        return self.left in self.right

class And(Operator):
    token = 'and'
    p = 1
    def op(self):
        return self.left and self.right

class Or(Operator):
    token = 'or'
    p = 1
    def op(self):
        return self.left == self.right

class Starts(Operator):
    token = ':='
    p = 0
    def op(self):
        return str(self.left).startswith(str(self.right))

class Ends(Operator):
    token = '=:'
    p = 0
    def op(self):
        return str(self.left).endswith(str(self.right))

class Literal(object):
    token = '.'
    p = -2
    def __init__(self, item):
        self.item = item

    def __str__(self):
        if self.item is None:
            return ''
        return str(self.item)

    def __repr__(self):
        if self.item is None:
            return 'L(%s)' % repr('')
        return 'L(%s)' % repr(self.item)

class Group(object):
    token = '*'
    p = -2
    def __init__(self, items):
        if len(items) == 3:
            self.left, self.op, self.right = items
        self.items = items

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        if len(self.items) == 3:
            return 'G(%s %s %s)' % (repr(self.left), repr(self.op), repr(self.right))
        else:
            return 'G(%s)' % ' '.join([repr(o) for o in self.items])



for cls in (Equals, Different, Superior, Inferior, SuperiorEq,
            InferiorEq, Not, In, And, Or, Starts, Ends,):
    Operator.add(cls)


class AccessRule(Registry):
    _class_id = 'AccessRule'

    def __init__(self, *args):
        """
        args = ('site.group', '=', 'BSD_hosts', 'and',
                'user.profile', '!=', 'users')
        args = "|site.group|=|BSD_hosts|and|user.profile|!=|users|"
        """
        if len(args) == 1 and isinstance(args[0], str):
            if args[0][0] == '|':
                # XXX: naive parsing
                args = [ e for e in args[0].split('|') if e ]
            else:
                # TODO: implement better parsing with quotes
                pass

        self.elements = list(args)

        self.tree = self.parse(self.elements, [])

    def parse(self, args, tree):
        i = 0

        while i < len(args):
            op = Operator.get(args[i])
            if op:
                args[i] = op
                if op.token == 'not':
                    args.insert(i, Literal('NULL'))
                    i += 1
            elif args[i] in ('(', ')'):
                pass
            else:
                args[i] = Literal(args[i])
            i += 1

        args = self.hier_par(args)
        return self.hier_op(args)

    def hier_par(self, args):
        val = []
        i = 0
        while i < len(args):
            if args[i] == '(':
                v = self.hier_par(args[i+1:])
                val.append(v)
                i+= len(v)
            elif args[i] == ')':
                return Group(val)
            else:
                val.append(args[i])
            i += 1
        return Group(val)

    def hier_op(self, args):
        if len(args) <= 3:
            if isinstance(args, Group):
                return args 
            elif len(args) == 1:
                return args[0]
            else:
                return Group(args)
        max = -1
        for i in range(len(args)):
            if max < args[i].p:
                max = args[i].p
                maxi = i

        left = None
        if maxi >= 0:
            left = args[:maxi]

        right = None
        if maxi < len(args) - 1:
            right = args[maxi+1:]

        return Group([ self.hier_op(left), args[maxi], self.hier_op(right) ])


    def eval(self, namespace):
        return self.eval_r(self.tree, namespace)

    def eval_r(self, tree, namespace):
        if isinstance(tree, Group):
            #print tree, tree.op.token
            left, right = (self.eval_r(tree.left, namespace),
                           self.eval_r(tree.right, namespace))
            op = tree.op
            #print 'left=', left
            #print 'right=', left
            #print 'op=', op, op.__class__
            o = op(left, right)
            print o.op(), '=', o
            return o.op()
        else:
            tree = str(tree)
            for k in namespace:
                if tree.startswith(k+'.'):
                    tree = getattr(namespace[k], tree[len(k)+1:])
            return tree



class AccessControl(Registry):
    _class_id = 'AccessControl'
    
    @staticmethod
    def can_connect(self, clientinfo, site_id):
        pwdb = PasswordDatabase.get_instance()

    def add_rule(self, name, rule):
        self.rules.append(rule)

    """
    Attributes:
        proxy.state
        proxy.date
        proxy.time
        proxy.datetime

        client.username
        client.ip_address
        client.password
        client.pkey
        client.hostkey
        client.location

        profile.acl_data

        site.name
        site.ip
        site.port
        site.location
        site.description
        site.hostkey
        site.pkey

        user.name
        user.password
        user.pkey

    Operators:
        =
        !=
        >
        <
        >=
        <=
        in
        and
        or
        not
        :=     <- startswith
        =:     <- endswith
        (
        )

    """


if __name__ == '__main__':
    # example usage: the 3 following statements are equivalent
    ar = AccessRule("|site.group|=|BSD_hosts|and|not|(|user.profile|:=|users|)|")
    ar = AccessRule('site.group', '=', 'BSD_hosts', 'and',
        'not', '(', 'user.profile', ':=', 'users', ')')
    ar = AccessRule('site.group', '=', 'BSD_hosts', 'and',
        'not', 'user.profile', ':=', 'users')
    print ar.tree
    class A: pass
    namespace = {'site': A(), 'user': A(), }
    namespace['site'].group = 'BSD_hosts'
    namespace['user'].profile = 'users_noobs'
    print ar.eval(namespace) # prints False
    namespace['user'].profile = 'admin'
    print ar.eval(namespace) # prints True


