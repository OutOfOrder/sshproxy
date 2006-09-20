#!/usr/bin/env python

import sys
import readline
import lex
import ryacc
import os
from copy import copy

from registry import Registry
import log

class Context(object):
    pass

class Parser(object):
    """
    Base class for a lexer/parser that has the rules defined as methods
    """
    tokens = ()
    precedence = ()


    def __init__(self, **kw):
        self.debug = kw.get('debug', 0)
        self.parse_result = None # undefined
        try:
            modname = os.path.split(os.path.splitext(__file__)[0])[1] \
                                + "_" + self.__class__.__name__
        except:
            modname = "parser"+"_"+self.__class__.__name__
        self.debugfile = modname + ".dbg"
        self.tabmodule = modname + "_" + "parsetab"
        #print self.debugfile, self.tabmodule

        # Build the lexer and parser
        self.ctx = Context()
        ryacc.ctx = self.ctx
        self.lexer = lex.lex(module=self, debug=self.debug)
        self.parser = ryacc.yacc(module=self,
                  debug=self.debug,
                  debugfile=self.debugfile,
                  tabmodule=self.tabmodule,
                  write_tables=0,
                  optimize=1)

    def run(self):
        while 1:
            try:
                s = raw_input('acl > ')
            except EOFError:
                break
            if not s: continue     
            if self.debug:
                self.lexer.input(s)
                while True:
                    tok = self.lexer.token()
                    if not tok: break
                    print tok
            print self.eval(s)

    def eval(self, s):
        if self.debug:
            self.lexer.input(s)
            while True:
                tok = self.lexer.token()
                if not tok: break
                print tok
        # save the context
        save_ctx = ryacc.ctx
        # put in place our own context
        ryacc.ctx = self.ctx
        self.parser.parse(s, lexer=self.lexer)
        # restore the context back
        ryacc.ctx = save_ctx
        return self.parse_result

    
class ACLRuleParser(Registry, Parser):
    _class_id = 'ACLRuleParser'
    def __reginit__(self, namespace=None, **kw):
        if namespace is None:
            self.namespace = {}
        else:
            self.namespace = namespace
        self.vars = { }
        self.consts = {
                'True': True,
                'False': False,
                'None': None,
                }
#        Parser.__reginit__(self, **kw)

    def get_ns(self):
        ns ={}
        ns.update(self.vars)
        ns.update(self.consts)
        ns.update(self.namespace)
        return ns

    def func_acl(self, *args):
        from acl import ACList
        if len(args) > 1:
            log.warning("Warning, acl() accepts only one argument")
        if isinstance(args[0], ACList):
            if len(args[0]):
                aclstr = args[0][0].name
                value = True in [ self.func_acl(arg.rule) for arg in args[0] ]
            else:
                aclstr = "None"
                value = False
        elif isinstance(args[0], str):
            aclstr = args[0]
            subparser = ACLRuleParser(namespace=self.namespace)
            value = subparser.eval(args[0])
        else:
            aclstr = args[0]
            value = args[0]
        log.debug("ACL: %s '%s'" % (bool(value), aclstr))
        return value

    def func_split(self, *args):
        if len(args) > 1 or not isinstance(args[0], str):
            log.warning("Warning, split() accepts only one string argument")
        else:
            return args[0].split()

    def func(self, func, *args):
        thefunc = getattr(self, 'func_%s' % func, None)
        if thefunc is None:
            log.warning("Unknown func %s" % func)
            return False
        return thefunc(*args)


    ########## The parser itself

    tokens = [
        'NAME',
        'NUMBER',
        'COMA',
        'DOT',
        'SQCONST',
        'DQCONST',
        'PLUS',
        'MINUS',
        'EXP',
        'TIMES',
        'DIVIDE',
        'LPAREN',
        'RPAREN',
        'EQU',
        'SUP',
        'INF',
        'EQSUP',
        'EQINF',
        'DIFF',
        'NOT',
        'IN',
        'AND',
        'OR',
        'STARTS',
        'ENDS',
        ]

    t_ignore = " \t"

    # Tokens
    # the following long tokens need whitespaces to be eval'ed before t_NAME
    t_AND     = r'and                                '
    t_OR      = r'or                                 '
    t_NOT     = r'not                                '
    t_IN      = r'in                                 '
    t_STARTS  = r':='
    t_ENDS    = r'=:'
    t_COMA    = r','
    t_DOT     = r'\.'
    t_PLUS    = r'\+'
    t_MINUS   = r'-'
    t_EXP     = r'\*\*'
    t_TIMES   = r'\*'
    t_DIVIDE  = r'/'
    t_EQU     = r'=='
    t_DIFF    = r'!='
    t_SUP     = r'>'
    t_INF     = r'<'
    t_EQSUP   = r'>='
    t_EQINF   = r'<='
    t_LPAREN  = r'\('
    t_RPAREN  = r'\)'
    t_NAME    = r'[a-zA-Z_][a-zA-Z0-9_]*'
    t_SQCONST = r'\'([^\\\n]|(\\.))*?\''
    t_DQCONST = r'\"([^\\\n]|(\\.))*?\"'

    precedence = [
        ('left', 'OR'),
        ('left', 'AND'),
        ('right','RNOT'),
        ('left','EQU','DIFF', 'SUP', 'INF', 'EQSUP', 'EQINF'),
        ('left','PLUS','MINUS'),
        ('left','TIMES','DIVIDE'),
        ('left', 'EXP'),
        ('left','IN'),
        ('right','UMINUS'),
        ]

    def t_NUMBER(self, t):
        r"\d+"
        try:
            t.value = int(t.value)
        except ValueError:
            log.warning("Integer value too large %s" % t.value)
            t.value = False
        return t

    def t_newline(self, t):
        r"\n+"
        t.lineno += t.value.count("\n")
    
    def t_error(self, t):
        log.error("Illegal character '%s'" % t.value[0])
        t.skip(1)

    # Parsing rules
    def p_statement_expr(self, p):
        """
        statement : expression
        """
        #p[0] = p[1]
        self.parse_result = p[1]

    def p_expression_callfunc_expr(self, p):
        """
        expression : NAME LPAREN expression RPAREN
        """
        p[0] = self.func(p[1], p[3])

    def p_expression_callfunc_list(self, p):
        """
        expression : NAME LPAREN list RPAREN
        """
        p[0] = self.func(p[1], *p[3])

    def p_list_many(self, p):
        """
        list : list COMA expression
        """
        p[0] = p[1]
        p[0].append(p[3])

    def p_list_two(self, p):
        """
        list : expression COMA expression
        """
        p[0] = [ p[1], p[3] ]

    def p_expression_list(self, p):
        """
        expression : LPAREN list RPAREN
        """
        p[0] = p[2]

    def p_expression_bool(self, p):
        """
        expression : expression AND expression
                  | expression OR expression
        """
        #print [repr(p[i]) for i in range(0,4)]
        if p[2] == 'and':
            p[0] = p[1] and p[3]
        elif p[2] == 'or':
            p[0] = p[1] or p[3]

    def p_expression_binop(self, p):
        """
        expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression EXP expression
        """
        #print [repr(p[i]) for i in range(0,4)]
        try:
            if p[2] == '+'  : p[0] = p[1] + p[3]
            elif p[2] == '-': p[0] = p[1] - p[3]
            elif p[2] == '*': p[0] = p[1] * p[3]
            elif p[2] == '/': p[0] = p[1] / p[3]
            elif p[2] == '**': p[0] = p[1] ** p[3]
        except TypeError:
            p[0] = False

    def p_expression_test(self, p):
        """
        expression : expression EQU expression
                  | expression DIFF expression
                  | expression SUP expression
                  | expression INF expression
                  | expression EQSUP expression
                  | expression EQINF expression
                  | expression STARTS expression
                  | expression ENDS expression
                  | expression IN expression
        """
        #print [(repr(p[i]), type(p[i])) for i in range(0,4)]
        try:
            if p[2] == '=='  : p[0] = p[1] == p[3]
            elif p[2] == '!='  : p[0] = p[1] != p[3]
            elif p[2] == '>'  : p[0] = p[1] > p[3]
            elif p[2] == '<'  : p[0] = p[1] < p[3]
            elif p[2] == '>='  : p[0] = p[1] >= p[3]
            elif p[2] == '<='  : p[0] = p[1] <= p[3]
            elif p[2] == 'in'  : p[0] = p[1] in p[3]
            elif p[2] == ':='  : p[0] = str(p[1])[:len(p[3])] == p[3]
            elif p[2] == '=:'  : p[0] = str(p[1])[-len(p[3]):] == p[3]
        except TypeError:
            p[0] = False

    def p_expression_uminus(self, p):
        """
        expression : MINUS expression %prec UMINUS
        """
        try:
            p[0] = -p[2]
        except TypeError:
            p[0] = False

    def p_expression_rnot(self, p):
        """
        expression : NOT expression %prec RNOT
        """
        p[0] = not p[2]

    def p_expression_group(self, p):
        """
        expression : LPAREN expression RPAREN
        """
        p[0] = p[2]

    def p_expression_number(self, p):
        """
        expression : NUMBER
        """
        p[0] = p[1]

    def p_expression_string(self, p):
        """
        expression : SQCONST
                   | DQCONST
        """
        q = p[1][0]
        p[0] = p[1][1:-1].replace('\\'+q, q)

    def p_expression_name(self, p):
        'expression : NAME'
        try:
            p[0] = self.get_ns()[p[1]]
        except (LookupError, AttributeError):
            log.warning("ACL: Undefined name '%s'" % p[1])
            p[0] = False

    def p_expression_namespace(self, p):
        'expression : NAME DOT NAME'
        try:
            p[0] = self.get_ns()[p[1]][p[3]]
        except (LookupError, AttributeError):
            log.warning("ACL: Undefined name '%s.%s'" % (p[1], p[3]))
            p[0] = False

    def p_error(self, p):
        log.error("Syntax error at '%s'" % p.value)

class String(str):
    def __init__(self, s):
        self.string = s[1:-1].replace('\\"', '"')
        str.__init__(self, self.string)

    def __str__(self):
        return self.string

ACLRuleParser.register()

class ACLRuleParserInteractive(ACLRuleParser):
    _class_id = 'ACLRuleParserInteractive'
    t_EQUALS  = r'='
    def __reginit__(self, **kw):
        self.tokens.append('EQUALS')

        ACLRuleParser.__reginit__(self, **kw)

    def p_statement_assign(self, p):
        """
        statement : NAME EQUALS expression
        """
        if p[1] in self.namespace.keys():
            print "Cannot reassign a namespace"
            return
        self.vars[p[1]] = p[3]
        self.parse_result = p[3]

ACLRuleParserInteractive.register()


if __name__ == '__main__':
    # TODO: put this in a separate executable to test ACLs
    ns = {}
    ns['client'] = {
            'username': 'foo',
            'ip_addr': '1.2.3.4',
            'password': 'bar',
            'can_connect': 'site.login == "pulp"',
            }
    ns['site'] = {
            'name': 'fiction',
            'login': 'pulp',
            'port': '22',
            'ip_address': '12.23.45.56',
            }
    ns['proxy'] = {
            'time': '03:12',
            'date': '2006-07-22',
            'n_clients': '3',
            }
    ns['auth_admin'] = """client.ip_addr == "127.0.0.1" """

    if len(sys.argv) > 1:
        aclrule = ACLRuleParser(debug=0, namespace=ns)
        print aclrule.eval(' '.join(sys.argv[1:]))
    else:
        aclrule = ACLRuleParserInteractive(debug=0, namespace=ns)
        aclrule.run()
