#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-
#
# Copyright (C) 2005-2006 David Guerizec <david@guerizec.net>
#
# Last modified: Tue May 30 12:05:55 2006 by david
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


CTRL_A = '\x01'
CTRL_B = '\x02'
CTRL_C = '\x03'
CTRL_D = '\x04'
CTRL_E = '\x05'
CTRL_F = '\x06'
CTRL_G = '\x07'
CTRL_H = '\x08'
CTRL_I = '\x09'
CTRL_J = '\x0a'
CTRL_K = '\x0b'
CTRL_L = '\x0c'
CTRL_M = '\x0d'
CTRL_N = '\x0e'
CTRL_O = '\x0f'
CTRL_P = '\x10'
CTRL_Q = '\x11'
CTRL_R = '\x12'
CTRL_S = '\x13'
CTRL_T = '\x14'
CTRL_U = '\x15'
CTRL_V = '\x16'
CTRL_W = '\x17'
CTRL_X = '\x18'
CTRL_Y = '\x19'
CTRL_Z = '\x1a'
CTRL__ = '\x1f'

INS    = '\x1b\x5b\x32\x7e'
DEL    = '\x1b\x5b\x33\x7e'
END    = '\x1b\x5b\x46'
HOME   = '\x1b\x5b\x48'
PG_UP  = '\x1b\x5b\x35\x7e'
PG_DN  = '\x1b\x5b\x36\x7e'

F1     = '\x1b\x4f\x50'
F2     = '\x1b\x4f\x51'
F3     = '\x1b\x4f\x52'
F4     = '\x1b\x4f\x53'
F5     = '\x1b\x5b\x31\x35\x7e'
F6     = '\x1b\x5b\x31\x37\x7e'
F7     = '\x1b\x5b\x31\x38\x7e'
F8     = '\x1b\x5b\x31\x39\x7e'
F9     = '\x1b\x5b\x32\x30\x7e'
F10    = '\x1b\x5b\x32\x31\x7e'
F11    = '\x1b\x5b\x32\x33\x7e'
F12    = '\x1b\x5b\x32\x34\x7e'

TAB    = CTRL_I
SHFTAB = '\x1b\x5b\x5a'

ALT_0  = '\x1b\x30'
ALT_1  = '\x1b\x31'
ALT_2  = '\x1b\x32'
ALT_3  = '\x1b\x33'
ALT_4  = '\x1b\x34'
ALT_5  = '\x1b\x35'
ALT_6  = '\x1b\x36'
ALT_7  = '\x1b\x37'
ALT_8  = '\x1b\x38'
ALT_9  = '\x1b\x39'

ALT_NUMBERS = (ALT_0, ALT_1, ALT_2, ALT_3, ALT_4, ALT_5, ALT_6, ALT_7, ALT_8, ALT_9)

def get_alt_number(key):
    if key not in ALT_NUMBERS:
        return None
    return list(ALT_NUMBERS).index(key)

ARW_UP = '\x1b\x5b\x41'
