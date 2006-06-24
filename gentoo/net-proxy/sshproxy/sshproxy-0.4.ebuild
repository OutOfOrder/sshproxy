# Copyright 1999-2006 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit distutils

DESCRIPTION="sshproxy is an ssh gateway to apply ACLs on ssh connections"
HOMEPAGE="http://penguin.fr/sshproxy/"
SRC_URI="http://penguin.fr/sshproxy/download/${P}.tar.gz"

LICENSE="GPL"
SLOT="0"
KEYWORDS="~alpha ~amd64 ~ia64 ~ppc ~sparc ~x86"
IUSE="mysql"

DEPEND=">=dev-lang/python-2.4.0
		>=dev-python/paramiko-1.6
		mysql? ( >=dev-python/mysql-python-1.2.0 )"
RDEPEND=""

pkg_setup() {
	enewgroup ${PN}
	enewuser ${PN} -1 -1 /var/lib/sshproxy ${PN}
}


src_install () {
	distutils_src_install

	# init/conf files for sshproxy daemon
	newinitd ${FILESDIR}/sshproxyd.initd sshproxyd
	newconfd ${FILESDIR}/sshproxyd.confd sshproxyd
}

pkg_postinst () {
	einfo "If this is your first installation, run sshproxyd --wizard to"
	einfo "initialize the backend"
	distutils_pkg_postinst
}


