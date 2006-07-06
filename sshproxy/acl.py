#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 06, 03:45:29 by david
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

class ParseError(Exception):
    pass

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

    @staticmethod
    def list():
        return [ op.token for op in self._ops ]

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
        return self.left or self.right

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
        return '%s' % repr(self.item)

class Group(object):
    token = '*'
    p = -2
    def __init__(self, left, op, right):
        if op.token in ('.', '*'):
            raise ParseError('Unknown operator: %s' % repr(op))
        self.left, self.op, self.right = left, op, right

    def __getitem__(self, item):
        return self.items[item]

    def __len__(self):
        return len(self.items)

    def __str__(self):
        return ' ( %s %s %s ) ' % (str(self.left),
                                   str(self.op),
                                   str(self.right))

    def __repr__(self):
        return ' G( %s %s %s ) ' % (repr(self.left),
                                   repr(self.op),
                                   repr(self.right))



for cls in (Equals, Different, Superior, Inferior, SuperiorEq,
            InferiorEq, Not, In, And, Or, Starts, Ends,):
    Operator.add(cls)


class AccessRule(Registry):
    _class_id = 'AccessRule'

    def __init__(self, rule):
        tokens = self.tokenize(rule)

        self.tokens = list(tokens)
        self.rule = ' '.join(tokens)

        self.tree = self.parse(self.tokens)

    def _search_tok(self, s, i, *toks):
        indexes = [len(s)]
        s = s[i:]
        for tok in toks:
            if tok in s:
                indexes.append(s.index(tok))
        return i + min(indexes)

    def tokenize(self, s):
        i = 0
        l = 0
        tokens = []
        seps = []
        seps += ['>=', '<=', '!=', ':=', '=:']
        seps += ['=', '>', '<']
        seps += [' ', '\t', '\n', '\r', '"']
        seps += ['(', ')']
        # I don't know why the sort function does not work...
        #def sort_seps(x, y):
        #    r = len(x) > len(y)
        #    return r
        #seps.sort(cmp=sort_seps)
        while i < len(s):
            j = i
            i = self._search_tok(s, i, *seps)
            if i >= len(s):
                break
            if s[i] in (' ', '\t', '\n', '\r'):
                if j < i:
                    tokens.append(s[j:i])
            elif s[i] == '"':
                if j < i:
                    raise ParseError('Missing separator: ...%s...'
                                                        % s[max(i-5, 0):i+5])
                i += 1
                j = i
                while True:
                    i = self._search_tok(s, i, '"', '\\"')#, '\\\\')
                    if i >= len(s):
                        raise ParseError('Unterminated quoted string')
                    if s[i:i+2] != '\\"':
                        break
                    else:
                        i += 2
                if j <= i < len(s):
                    if s[i] not in seps:
                        raise ParseError('Missing separator: ...%s...'
                                                        % s[max(i-5, 0):i+5])
                    tokens.append(s[j:i].replace('\\"', '"'))
            else:
                if j < i:
                    tokens.append(s[j:i])
                for t in seps:
                    lt = len(t)
                    if s[i:i+lt] == t:
                        tokens.append(s[i:i+lt])
                        i += lt - 1
                        j = i
                        break
            i += 1
        #tokens.append(s[j:])
        return tokens
            
    def parse(self, tokens):
        i = 0

        while i < len(tokens):
            op = Operator.get(tokens[i])
            if op:
                tokens[i] = op
                # exception for not that does take only one argument
                if op.token == 'not':
                    tokens.insert(i, Literal('NULL'))
                    i += 1
            elif tokens[i] in ('(', ')'):
                pass
            else:
                tokens[i] = Literal(tokens[i])
            i += 1

        # treat parenthesis first
        tokens = self.hier_par(tokens)
        # make a tree with operators
        return self.hier_op(tokens)

    def hier_par(self, tokens, i=0, l=0):
        val = []
        lt = len(tokens)
        while i < lt:
            if str(tokens[i]) == '(':
                v, j = self.hier_par(tokens, i+1, l+1)
                val.append(v)
                i = j
            elif str(tokens[i]) == ')':
                return val, i
            else:
                val.append(tokens[i])
            i += 1
        return val

    def _find_center_op(self, tokens):
        max = -1
        maxi = 1
        for i in range(len(tokens)):
            if isinstance(tokens[i], list):
                tokens[i] = self.hier_op(tokens[i])
                continue
            if max < tokens[i].p:
                max = tokens[i].p
                maxi = i
        if maxi < len(tokens):
            return [tokens[:maxi], tokens[maxi], tokens[maxi+1:]]
        else:
            return tokens[0]

    def hier_op(self, tokens):
        all = self._find_center_op(tokens)
        if isinstance(all, list) and len(all) == 3:
            left, op, right = all
        else:
            return all

        if len(left) == 1:
            left = left[0]
        else:
            left = self.hier_op(left)
        if len(right) == 1:
            right = right[0]
        else:
            right = self.hier_op(right)

        ret = Group(left, op, right)
        return ret


    def eval(self, namespace):
        return bool(self.eval_r(self.tree, namespace))

    def eval_r(self, tree, namespace):
        if isinstance(tree, Group): # and len(tree) == 3:
            left, right = (self.eval_r(tree.left, namespace),
                           self.eval_r(tree.right, namespace))
            op = tree.op
            o = op(left, right)
            print o.op(), '=', o
            return bool(o.op())
        else:
            tree = str(tree)
            for k in namespace:
                if tree.startswith(k+'.'):
                    attr = tree[len(k)+1:]
                    if hasattr(namespace[k], attr):
                        tree = getattr(namespace[k], attr)
                    else:
                        tree = ''
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
    import sys, datetime, time
    # example usage:
    arstr = '''
        ((site.group in "BSD hosts"))
        and((site.stime<=proxy.time)
        and(site.etime>=proxy.time))
        and(site.stime<=proxy.time
        and site.etime>=proxy.time)
        and not("noobs"=:user.profile)
        '''
    arstr = '''
        (site.group in "BSD hosts"
        and(site.stime<=proxy.time))
        '''
    try:
        ar = AccessRule(arstr)
    except ParseError, msg:
        print 'Error:', msg
        sys.exit(1)
    #print repr(ar.tree)
    class A(dict):
        def __init__(self, **kw):
            for k in kw:
                setattr(self, k, str(kw[k]))
                self[k] = str(kw[k])

        def __setattr__(self, k, v):
            dict.__setattr__(self, k, v)
            self[k] = v
            

    namespace = {
            'site': A(group='BSD', stime='08:00', etime='18:00'),
            'user': A(profile='users_noobs'),
            'client': A(username='david'),
            'proxy': A(time=time.strftime('%H:%M')),
            }


    print ar.rule
    namespace['proxy'].time = '07:00'
    print namespace
    print ar.eval(namespace) # prints False
    namespace['proxy'].time = '10:00'
    print namespace
    print ar.eval(namespace) # prints False
    namespace['user'].profile = 'admin'
    print namespace
    print ar.eval(namespace) # prints True
    namespace['proxy'].time = '07:00'
    print namespace
    print ar.eval(namespace) # prints False

