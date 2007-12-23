#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2006 Jul 31, 01:55:01 by david
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


# Note to readers: This module is quite ugly, and will need a
# great amount of refactoring in the future. (DG)

class MenuSep(object):
    def __init__(self, title=''):
        self.title = title

    def __str__(self):
        return self.title

class BaseMenuItem(object):
    clear = "\x1b\x5b\x48\x1b\x5b\x32\x4a\n"
    def __init__(self, title, description=None, *items, **data):
        self.title = title
        self.description = description and str(description) or ''
        self.items = list(items)
        self.data = data

    def show(self):
        print self.clear,
        print self.title
        print '='*len(self.title)
        print
        if self.description.strip():
            print self.description.ljust(40)
            print


class MenuStub(BaseMenuItem):
    clear = '\n'
    def __init__(self, title, description, value):
        BaseMenuItem.__init__(self, title, description)
        self.value = value

    def __str__(self):
        return '%s [%s]' % (self.title, self.value)

    def __call__(self):
        self.show()
        print "No action possible for this item"
        raw_input("Press enter")
        return self.value

class MenuSwitch(object):
    def __init__(self, title, value, state, cb=None, **data):
        self.title = title
        self.value = value
        self.state = state
        self.cb    = cb
        self.data  = data

    def __str__(self):
        state = self.state and '*' or ' '
        return '%s %s [%s]' % (state, self.title, self.value)

    def __call__(self):
        state = not self.state
        if self.cb and self.cb(self.value, state, **self.data) is False:
            return
        self.state = state

class MenuInput(BaseMenuItem):
    clear = '\n'
    def __init__(self, title, description=None, default=None, cb=None, **data):
        BaseMenuItem.__init__(self, title, description, *[], **data)
        self.default = default
        self.cb      = cb

    def __str__(self):
        return '%s [%s]' % (self.title, self.default)

    def __call__(self):
        self.show()
        while True:
            value = raw_input('%s [%s] ' %
                              (self.title, self.default)) or self.default
            if self.cb:
                if self.cb(value, **self.data) is not False:
                    break
            else:
                break
        self.default = value

class MenuPassword(MenuInput):
    def __init__(self, title, description=None, default=None, cb=None, **data):
        BaseMenuItem.__init__(self, title, description, *[], **data)
        self._default = default
        self.default  = '*'*min(len(self._default), 10)
        self._cb      = cb
        if cb:
            self.cb   = self.cb_wrap

    def cb_wrap(self, value, **data):
        if value == '*'*10:
            value = None
        return self._cb(value, **data)


class Menu(BaseMenuItem):
    question = "Please make a choice: "
    back_text = "Back"
    def add(self, item):
        if isinstance(item, list):
            for entry in item:
                self.items.append(entry)
        else:
            self.items.append(item)

    def __iter__(self):
        for item in self.items:
            if isinstance(item, MenuSub):
                for subitem in item:
                    yield subitem
            else:
                yield item

    def show(self):
        BaseMenuItem.show(self)
        i = 0
        for item in self:
            if isinstance(item, MenuSep):
                print str(item)
                continue
            print "%d. %s" % (i+1, str(item))
            i += 1
        print
        print "0. %s" % self.back_text
        print

    def choice(self, default=None):
        question = self.question
        if default is not None:
            question = question + "[%s] " % default
        return raw_input(question) or default

    def response(self, choice):
        items = [ item for item in self if not isinstance(item, MenuSep) ]
        if choice > len(items):
            return
        return items[choice - 1]()

    def __str__(self):
        return self.title

    def __call__(self):
        if not len(self.items):
            BaseMenuItem.show(self)
            print "No action possible for this item"
            raw_input("Press enter")
            return
        while True:
            try:
                self.show()
                try:
                    choice = int(self.choice())
                except (TypeError, ValueError):
                    continue
                if choice == 0:
                    return
                self.response(choice)
            except ValueError:
                pass

class MenuChoice(Menu):
    clear = '\n'
    question = "Pick a value: "
    def __init__(self, title, description, default, cb,
                                                    *items, **data):
        Menu.__init__(self, title, description, *items, **data)
        self.default = default
        self.cb      = cb

    def __str__(self):
        return '%s [%s]' % (self.title, self.default)

    def show(self):
        BaseMenuItem.show(self)
        i = 0
        for title, name in self.items:
            print "%d. %s (%s)" % (i+1, title, name)
            i += 1
        print
        print "0. Keep %s" % self.default
        print

    def response(self, choice):
        items = [ item for item in self.items ]
        if choice > len(items):
            return
        return self.cb(items[choice - 1][1], **self.data)

    def __call__(self):
        if not len(self.items):
            print "No action possible for this item"
            raw_input("Press enter")
            return
        while True:
            try:
                self.show()
                try:
                    choice = int(self.choice())
                except (TypeError, ValueError):
                    continue
                if choice == 0:
                    return
                return self.response(choice)
            except ValueError:
                pass

class MenuSub(Menu):
    def sort(self):
        self.items.sort(lambda x, y: cmp(x.title, y.title))

    def remove(self, item):
        self.items.remove(item)
    
    def insert(self, pos, item):
        self.items.insert(pos, item)

class MenuDyn(MenuSub):
    def __init__(self, generator, title, description=None, *items, **data):
        self.generator = generator
        Menu.__init__(self, title=title, description=description,
                                        *items, **data)

    def __iter__(self):
        self.items = self.generator()
        return MenuSub.__iter__(self)

    def show(self):
        self.items = self.generator()
        return MenuSub.show(self)

    def __call__(self):
        self.items = self.generator()
        return MenuSub.__call__(self)


