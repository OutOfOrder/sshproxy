all:
	echo "make clean to clean all unneeded files"

clean:
	find -name '*.pyc' -exec rm \{\} \;
	rm -f sshproxy.log paramiko.log
