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

DEPEND="=net-proxy/sshproxy-0.5.0"

S=${WORKDIR}/${MY_P}

src_install () {
	dodir /usr/lib/sshproxy
	insinto /usr/lib/sshproxy/console_extra
	doins ${S}/lib/console_extra/*
	insinto /usr/lib/sshproxy/acl_funcs
	doins ${S}/lib/acl_funcs/*
}

pkg_postinst () {
	distutils_pkg_postinst

	einfo "You may want to enable plugins with the following command:"
	einfo "    sshproxy-setup -c /etc/sshproxy -u sshproxy"
}

