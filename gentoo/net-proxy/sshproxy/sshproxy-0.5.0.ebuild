# Copyright 1999-2006 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: /var/cvsroot/gentoo-x86/net-proxy/sshproxy/sshproxy-0.4.3.ebuild,v 1.1 2006/07/15 15:07:17 mrness Exp $

inherit distutils

DESCRIPTION="sshproxy is an ssh gateway to apply ACLs on ssh connections"
HOMEPAGE="http://penguin.fr/sshproxy/"
SRC_URI="http://penguin.fr/sshproxy/download./${P}.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE="mysql"

DEPEND=">=dev-lang/python-2.4.0
		>=dev-python/paramiko-1.6
		mysql? ( =net-proxy/sshproxy-backend-mysql-0.5.0 )"

pkg_setup() {
	enewgroup sshproxy
	enewuser sshproxy -1 -1 /var/lib/sshproxy sshproxy
}

src_install () {
	distutils_src_install

	diropts -o sshproxy -g sshproxy -m0750
	dodir /var/lib/sshproxy
	keepdir /var/lib/sshproxy
	dodir /var/lib/sshproxy/log
	
	# Create a default sshproxy.ini
	dodir /etc/sshproxy
	keepdir /etc/sshproxy
	insopts -o sshproxy -g sshproxy -m0600
	insinto /etc/sshproxy
	doins ${FILESDIR}/sshproxy.ini
	BLOWFISH_SECRET="${RANDOM}${RANDOM}${RANDOM}${RANDOM}"
	sed -i -e "s/%BLOWFISH_SECRET%/${BLOWFISH_SECRET}/g" \
						${D}/etc/sshproxy/sshproxy.ini

	# remove plugins bundled in other sshproxy-* ebuilds
	for p in $(ls ${D}/usr/lib/sshproxy/); do
		case "${p}" in
			file_db|get_client_scripts|disabled) ;;
			*) rm -rf ${D}/usr/lib/sshproxy/${p} ;;
		esac
	done
	# these are part of the sshproxy-clients ebuild
	rm -f ${D}/usr/bin/pssh
	rm -f ${D}/usr/bin/pscp

	# init/conf files for sshproxy daemon
	newinitd "${FILESDIR}/sshproxyd.initd" sshproxyd
	newconfd "${FILESDIR}/sshproxyd.confd" sshproxyd
}

pkg_postinst () {
	pkg_setup #for creating the user when installed from binary package

	distutils_pkg_postinst

	echo
	einfo "If this is your first installation, run"
	einfo "   emerge --config =${CATEGORY}/${PF}"
	einfo "to initialize the backend."
	echo
	einfo "There is no need to install sshproxy on a client machine."
	einfo "You can connect to a SSH server using this proxy by running"
	einfo "   ssh -tp PROXY_PORT PROXY_HOST REMOTE_USER@REMOTE_HOST"
}

pkg_config() {
	INITD_STARTUP="/etc/init.d/sshproxyd start" chroot "${ROOT}" \
						sshproxy-setup -u sshproxy -c /etc/sshproxy
}
