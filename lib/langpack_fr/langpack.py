#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 David Guerizec <david@guerizec.net>
#
# Last modified: 2007 Dec 08, 20:29:13 by david
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

from sshproxy import get_class


I18n = get_class("I18n")

class LangPack_fr(I18n):

    encoding = 'utf8'
    messages = {
        1557792624: u"exécute des commandes d'administration",
        -2139151278: u"liste les sites autorisés",
        1318597108: u"ERREUR: %s n'existe pas dans votre environnement\n",
        433505454: u"ERREUR: Vous n'êtes pas autorisé à ouvrir une "
                    "session shell sur %s\n",
        -1260436857: u"""
        kill user@site
        
        Ferme toutes les connections vers user@site.
        """,
        774749702: u"""
        Affiche le nombre de connexions actives.
        """,
        -2011098661: u"""
        Recharge les règles ACL.
        """,
        -1575399941: u"""
        Affiche la liste des utilisateurs connectés.
        """,
        1992087534: u"""
        tag_site [user@]site [tag=value ...]
        
        Ajoute ou modifie un tag de site.
        Si aucun tag n'est fourni, affiche tous les tags du site.
        Si un tag n'a pas de valeur, il est supprimé.
        """,
        }


LangPack_fr.register()

if __name__ == '__main__':
    langpack = LangPack_fr()
    for message in langpack.messages.values():
        print langpack._(message)

