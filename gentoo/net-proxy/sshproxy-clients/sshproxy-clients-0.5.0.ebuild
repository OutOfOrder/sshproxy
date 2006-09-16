# Copyright 1999-2006 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: /var/cvsroot/gentoo-x86/net-proxy/sshproxy/sshproxy-0.4.3.ebuild,v 1.1 2006/07/15 15:07:17 mrness Exp $

MY_P="sshproxy-0.5.0"
DESCRIPTION="sshproxy is an ssh gateway to apply ACLs on ssh connections"
HOMEPAGE="http://penguin.fr/sshproxy/"
SRC_URI="http://penguin.fr/sshproxy/download./${MY_P}.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~x86"

IUSE=""

DEPEND="app-shells/bash
		net-misc/openssh"

S=${WORKDIR}/${MY_P}

src_install () {
	dobin ${S}/bin/pssh
	dobin ${S}/bin/pscp
}

pkg_postinst () {
	echo
	einfo "Don't forget to set up the following environment variables"
	einfo "   SSHPROXY_HOST (default to localhost)"
	einfo "   SSHPROXY_PORT (default to 2242)"
	einfo "   SSHPROXY_USER (default to $USER)"
	einfo "for each sshproxy user."
	echo
}

