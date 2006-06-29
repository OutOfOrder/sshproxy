# Copyright 1999-2006 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit distutils

DESCRIPTION="sshproxy is an ssh gateway to apply ACLs on ssh connections"
HOMEPAGE="http://penguin.fr/sshproxy/"
SRC_URI="http://penguin.fr/sshproxy/download/${P}.tar.gz"

LICENSE="GPL"
SLOT="0"
KEYWORDS="~x86"
IUSE="mysql"

DEPEND=">=dev-lang/python-2.4.0
		>=dev-python/paramiko-1.6
		mysql? ( >=dev-python/mysql-python-1.2.0 )"

pkg_setup() {
	enewgroup sshproxy
	enewuser sshproxy -1 -1 /var/lib/sshproxy sshproxy
}

src_install () {
	distutils_src_install

	diropts -o sshproxy -g sshproxy -m0750
	dodir /var/lib/sshproxy
	keepdir /var/lib/sshproxy

	# init/conf files for sshproxy daemon
	newinitd "${FILESDIR}/sshproxy.initd" sshproxyd
}

pkg_postinst () {
	pkg_setup #for creating the user when installed from binary package

	distutils_pkg_postinst

	echo
	einfo "If this is your first installation, run"
	einfo "   emerge --config =${CATEGORY}/${PF}"
	einfo "to initialize the backend."
}

pkg_config() {
	HOME=/var/lib/sshproxy chroot "${ROOT}" \
		INITD_STARTUP="/etc/init.d/sshproxyd start" /usr/bin/sshproxyd --wizard
}
