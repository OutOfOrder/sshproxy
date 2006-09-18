# Copyright 1999-2006 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
# $Header: $

MY_P="sshproxy-0.5.0-beta5"
DESCRIPTION="sshproxy is an ssh gateway to apply ACLs on ssh connections"
HOMEPAGE="http://penguin.fr/sshproxy/"
SRC_URI="http://penguin.fr/sshproxy/download/${MY_P}.tar.gz"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE=""

DEPEND="=net-proxy/sshproxy-${PV}
		>=dev-python/mysql-python-1.2.0"

S=${WORKDIR}/${MY_P}

src_install () {
	dodir /usr/lib/sshproxy
	insinto /usr/lib/sshproxy/mysql_db
	doins ${S}/lib/mysql_db/*
	insinto /usr/share/sshproxy/mysql_db
	doins ${S}/misc/mysql_db.sql
	doins ${S}/misc/sshproxy-mysql-user.sql
}

pkg_postinst () {
	echo
	einfo "If this is your first installation, run"
	einfo "   emerge --config =${CATEGORY}/${PF}"
	einfo "to initialize the backend."
	echo
}

pkg_config() {
	DB_NAME=sshproxy
	PASSWD="${RANDOM}${RANDOM}${RANDOM}${RANDOM}"
	SHARE=/usr/share/sshproxy/mysql_db

	ewarn "When prompted for a password, please enter your MySQL root password"
	ewarn

	echo '' | mysql -u root -p ${DB_NAME} > /dev/null 2> /dev/null
	if [ "$?" -ne 0 ]; then
		einfo "Creating sshproxy MySQL database \"$DB_NAME\""
		/usr/bin/mysqladmin -u root -p create $DB_NAME

		einfo "Creating sshproxy MySQL user"
		sed -e "s/sshproxypw/${PASSWD}/g" ${SHARE}/sshproxy-mysql-user.sql \
			| /usr/bin/mysql -u root -p $DB_NAME

		einfo "Creating sshproxy MySQL tables"
		/usr/bin/mysql -u root -p $DB_NAME < ${SHARE}/mysql_db.sql

	else
		ewarn "Database ${DB_NAME} already exists"
		ewarn "If you want to replace it, issue the following command:"
		ewarn "    /usr/bin/mysqladmin -u root -p drop $DB_NAME"
	fi
	echo
	einfo "You have to configure sshproxy with the following command:"
	einfo "    sshproxy-setup -u sshproxy -c /etc/sshproxy"
	einfo "Then you can choose the mysql_db backend for either client,"
	einfo "acl or site database, and enter the following information:"
	einfo "    1. Database host [localhost]"
	einfo "	   2. Database user [sshproxy]"
	einfo "	   3. Database password [${PASSWD}]"
	einfo "	   4. Database name [sshproxy]"
	einfo "	   5. Database port [3306]"
}
