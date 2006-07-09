#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 09, 14:51:00 by david
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

class ParseError(Exception):
    pass


class Operator(object):
    _ops = {}
    is_func = False
    p = 0
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
    p = 5
    def op(self):
        return self.left == self.right

class Different(Operator):
    token = '!='
    p = 5
    def op(self):
        return self.left != self.right

class Superior(Operator):
    token = '>'
    p = 5
    def op(self):
        return self.left > self.right

class Inferior(Operator):
    token = '<'
    p = 5
    def op(self):
        return self.left < self.right

class SuperiorEq(Operator):
    token = '>='
    p = 5
    def op(self):
        return self.left >= self.right

class InferiorEq(Operator):
    token = '<='
    p = 5
    def op(self):
        return self.left <= self.right

class In(Operator):
    token = 'in'
    p = 5
    def op(self):
        return self.left in self.right

class And(Operator):
    token = 'and'
    p = 9
    def op(self):
        return self.left and self.right

class Or(Operator):
    token = 'or'
    p = 9
    def op(self):
        return self.left or self.right

class Starts(Operator):
    token = ':='
    p = 5
    def op(self):
        return str(self.left).startswith(str(self.right))

class Ends(Operator):
    token = '=:'
    p = 5
    def op(self):
        return str(self.left).endswith(str(self.right))

class Function(Operator):
    is_func = True
    p = 4
    def __str__(self):
        return '%s(%s)' % (self.token, repr(self.right))

    def __repr__(self):
        return '%s(%s)' % (self.token, repr(self.right))

class Not(Function):
    token = 'not'
    def call(self, namespace):
        return not self.left.eval(namespace, self.right)

class Int(Function):
    token = 'int'
    def call(self, namespace):
        result = self.left.eval(namespace, self.right)
        try:
            result = int(result)
            return result
        except ValueError:
            return False

class List(Function):
    token = 'list'
    def call(self, namespace):
        items = self.left.eval(namespace, self.right)
        return items.split()

class Acl(Function):
    token = 'acl'
    def call(self, namespace):
        acl = self.left.eval(namespace, self.right)
        return self.left.eval(namespace,
                              ACLDB().check(acl, **namespace))

class Literal(str):
    token = 's'
    p = 0
    def __init__(self, item):
        str.__init__(self, item)

class Token(str):
    token = '1'
    p = 0
    def __init__(self, item):
        str.__init__(self, item)


    def __repr__(self):
        return str(self)

class Const(object):
    token = 'A'
    p = 0
    _constants = {
            'True': True,
            'False': False,
            }

    def __init__(self, item):
        self.item = self.get_constant(item)

    @staticmethod
    def get_int(i):
        try:
            return int(i)
        except ValueError:
            return None

    @classmethod
    def get_constant(cls, token):
        if token in cls._constants.keys():
            return cls._constants[token]
        return cls.get_int(token)

    @classmethod
    def is_constant(cls, token):
        if token in cls._constants.keys():
            return True
        return cls.get_int(token) is not None



class Group(object):
    token = '3'
    p = -2
    def __init__(self, left, op, right):
        if op.token in ('.', '*'):
            raise ParseError('Unknown operator: %s' % repr(op))
        self.left, self.op, self.right = left, op, right

    def __str__(self):
        return ' ( %s %s %s ) ' % (str(self.left),
                                   str(self.op),
                                   str(self.right))

    def __repr__(self):
        return ' G( %s %s %s ) ' % (repr(self.left),
                                   repr(self.op),
                                   repr(self.right))



for cls in (Equals, Different, Superior, Inferior, SuperiorEq,
            InferiorEq, In, And, Or, Starts, Ends, Not, Int, List, Acl):
    Operator.add(cls)


class ACLRule(Registry):
    _class_id = 'ACLRule'

    def __reginit__(self, name, rule):
        self.name = name
        tokens = self.tokenize('( %s )' % rule)

        self.tokens = list(tokens)
        rule = []
        for token in tokens:
            if isinstance(token, Literal):
                token = '"%s"' % token
            rule.append(token)

        self.rule = ' '.join(rule)

        self.tree = self.parse(self.tokens)

    #def __repr__(self):
    #    return '[repr] %s: %s' % (self.name, self.rule)

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
        seps += [' ', '\t', '\n', '\r']
        seps += ['(', ')', '"']
        seps += ['=', '!=']
        seps += ['>', '>=', '<', '<=']
        seps += [':=', '=:']
        seps.sort(cmp=lambda x, y: cmp(len(y), len(x)))
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
                    tokens.append(Literal(s[j:i].replace('\\"', '"')))
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
            if not isinstance(tokens[i], Literal):
                op = Operator.get(tokens[i])
                if op:
                    tokens[i] = op
                    # exception for functions that does take only one argument
                    if op.is_func:
                        tokens.insert(i, Token('NULL'))
                        i += 1
                elif tokens[i] in ('(', ')'):
                    pass
                elif Const.is_constant(tokens[i]):
                    tokens[i] = Const(tokens[i])
                else:
                    tokens[i] = Token(tokens[i])
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
                try:
                    v, j = self.hier_par(tokens, i+1, l+1)
                except ValueError:
                    raise ParseError('Parenthesis count mismatch in rule %s:\n'
                                                '%s' % (self.name, self.rule))

                val.append(v)
                i = j
            elif str(tokens[i]) == ')':
                return val, i
            else:
                val.append(tokens[i])
            i += 1
        return val

    def _find_center_op(self, tokens):
        max = 1
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
            try:
                return tokens[0]
            except IndexError:
                raise ParseError("Parse error, check your ACL rules.")

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


    def eval(self, namespace, tree=None):
        if tree is None:
            tree = self.tree
        return self.eval_r(tree, namespace)

    def eval_r(self, tree, namespace):
        if isinstance(tree, Group): # and len(tree) == 3:
            op = tree.op
            if op.is_func:
                left = self
                right = tree.right
            else:
                left, right = (self.eval_r(tree.left, namespace),
                               self.eval_r(tree.right, namespace))
            o = op(left, right)
            if op.is_func:
                result = o.call(namespace)
            else:
                result = o.op()
            #print result, '=', o
            return result
        elif isinstance(tree, Const):
            return tree.item
        elif isinstance(tree, Token):
            if tree[:6] == 'proxy.':
                value = self.proxy_dyn_namespace(tree[6:], namespace)
                if value is not None:
                    return value
            for k in namespace.keys():
                if tree.startswith(k+'.'):
                    attr = tree[len(k)+1:]
                    if namespace[k].has_key(attr):
                        item = namespace[k][attr]
                        if isinstance(item, ACLRule):
                            return namespace[k][attr]
                        else:
                            return namespace[k][attr]
            raise ParseError('Unknown identifier or missing quotes around %s.'
                                                                        % tree)
        else:
            return tree

    def proxy_dyn_namespace(self, tag, namespace):
        if tag == 'time':
            return str(datetime.datetime.now().strftime("%H:%M"))
        elif tag == 'date':
            return str(datetime.datetime.now().strftime("%Y-%m-%d"))
        elif tag == 'datetime':
            return str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        elif tag == 'doy':
            return datetime.datetime.now().strftime("%j")
        elif tag == 'week':
            return str(datetime.datetime.now().strftime("%W"))
        elif tag == 'unixtime':
            return int(time.time())
        elif tag == 'dow':
            return str(datetime.datetime.now().strftime("%w"))
        return None


ACLRule.register()


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
            value = str(value)
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


class ACLDB(Registry):
    _class_id = 'ACLDB'
    _singleton = True
    
    def __reginit__(self):
        self.rules = []
        self.load_rules()

    def load_rules(self):
        pass

    def save_rules(self):
        pass

    def add_rule(self, acl, rule):
        if rule is None:
            rule = ACLRule(acl, 'False')
        elif not isinstance(rule, ACLRule):
            rule = ACLRule(acl, str(rule))
        self.rules.append((acl, rule))

    def check(self, acl, **namespaces):
        namespace = {}
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
            for rule in self.rules:
                if rule[0] == acl:
                    match = repr(rule[1].rule)
                    if rule[1].eval(namespace):
                        result = True
                        break
                    else:
                        result = False

        if result is None:
            result = False
            #print 'ACL', acl, 'not found'
        else:
            #print 'ACL', acl, result, match
            pass
        return result


ACLDB.register()


