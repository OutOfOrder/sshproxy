all:
	echo "make clean to clean all unneeded files"

build:
	python setup.py build

install:
	python setup.py install


clean:
	find -name '*.pyc' -exec rm \{\} \;
	rm -rf build
