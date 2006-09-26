# Copyright 1999-2006 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

inherit distutils

DESCRIPTION="sshproxy is an ssh gateway to apply ACLs on ssh connections"
HOMEPAGE="http://penguin.fr/sshproxy/"
SRC_URI="http://penguin.fr/sshproxy/download/${P}.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~x86"

IUSE="mysql	minimal clientsonly"
# mysql: install the mysql_db backend driver
# minimal: do not install extra plugins
# clientsonly: install only the client wrappers

RDEPEND="!clientsonly? (
			>=dev-lang/python-2.4.3
			>=dev-python/paramiko-1.6.2
			mysql? >=dev-python/mysql-python-1.2.0
		)
		net-misc/openssh
		"

DEPEND="${RDEPEND}"

pkg_setup() {
	enewgroup sshproxy
	enewuser sshproxy -1 -1 /var/lib/sshproxy sshproxy
}

src_install () {
	dobin ${S}/bin/pssh
	dobin ${S}/bin/pscp
	if ! use clientsonly; then
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
	
		rm -rf ${D}/usr/lib/sshproxy/spexpect
		if use minimal; then
			for p in acl_funcs console_extra logusers; do
				rm -rf ${D}/usr/lib/sshproxy/${p}
			done
		else
			(   # initialize a raisonable value for the logusers plugin
				echo
				echo "[logusers]"
				echo "logdir = /var/lib/sshproxy/logusers"
				echo
			) >> ${D}/etc/sshproxy/sshproxy.ini
		fi
		
		# init/conf files for sshproxy daemon
		newinitd "${FILESDIR}/sshproxyd.initd" sshproxyd
		newconfd "${FILESDIR}/sshproxyd.confd" sshproxyd
	
		if use mysql; then
			insinto /usr/share/sshproxy/mysql_db
			doins ${S}/misc/mysql_db.sql
			doins ${S}/misc/sshproxy-mysql-user.sql
		else
			rm -rf ${D}/usr/lib/sshproxy/mysql_db
		fi
	fi
}

pkg_postinst () {
	if use clientsonly; then
		echo
		einfo "Don't forget to set the following environment variables"
		einfo "   SSHPROXY_HOST (default to localhost)"
		einfo "   SSHPROXY_PORT (default to 2242)"
		einfo "   SSHPROXY_USER (default to $USER)"
		einfo "for each sshproxy user."

	else
		pkg_setup #for creating the user when installed from binary package

		distutils_pkg_postinst

		echo
		einfo "If this is your first installation, run"
		einfo "   emerge --config =${CATEGORY}/${PF}"
		einfo "to initialize the backend and configure sshproxy."
		echo
		einfo "There is no need to install sshproxy on a client machine."
		einfo "You can connect to a SSH server using this proxy by running"
		einfo "   ssh -tp PROXY_PORT PROXY_HOST REMOTE_USER@REMOTE_HOST"
	fi
	echo
}

pkg_config() {
	if [ -d ${ROOT}/usr/lib/sshproxy/mysql_db ]; then
		DB_NAME=sshproxy
		PASSWD="${RANDOM}${RANDOM}${RANDOM}${RANDOM}"
		SHARE=${ROOT}/usr/share/sshproxy/mysql_db
	
		ewarn "When prompted for a password, enter your MySQL root password"
		ewarn
	
		echo '' | mysql -u root -p ${DB_NAME} > /dev/null 2> /dev/null
		if [ "$?" -ne 0 ]; then
			einfo "Creating sshproxy MySQL database \"$DB_NAME\""
			/usr/bin/mysqladmin -u root -p create $DB_NAME \
				|| die "Failed"
	
			einfo "Creating sshproxy MySQL user"
			sed -e "s/sshproxypw/${PASSWD}/g" ${SHARE}/sshproxy-mysql-user.sql \
				| /usr/bin/mysql -u root -p $DB_NAME \
					|| die "Failed"
	
			einfo "Creating sshproxy MySQL tables"
			/usr/bin/mysql -u root -p $DB_NAME < ${SHARE}/mysql_db.sql \
				|| die "Failed"
	
			cat <<EOF >> ${ROOT}/etc/sshproxy/sshproxy.ini

[client_db.mysql]
host = localhost
password = ${PASSWD}
db = sshproxy
user = sshproxy
port = 3306

[acl_db.mysql]
host = localhost
password = ${PASSWD}
db = sshproxy
user = sshproxy
port = 3306

[site_db.mysql]
host = localhost
password = ${PASSWD}
db = sshproxy
user = sshproxy
port = 3306

EOF

			sed -i -e 's/^\(\(acl\|client\|site\)_db = \)file_db/\1mysql_db/g' \
											${ROOT}/etc/sshproxy/sshproxy.ini

		else
			ewarn "Database ${DB_NAME} already exists"
			ewarn "If you want to replace it, issue the following command:"
			ewarn "    /usr/bin/mysqladmin -u root -p drop $DB_NAME"
			read -p "Hit any key to continue" key
		fi
		echo
	fi

	INITD_STARTUP="/etc/init.d/sshproxyd start" chroot "${ROOT}" \
						sshproxy-setup -u sshproxy -c /etc/sshproxy
}
