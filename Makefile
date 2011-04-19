PKGNAME=rpmhelper
VERSION=$(shell awk '/Version:/ { print $$2 }' ${PKGNAME}.spec)
RELEASE=$(shell awk '/Release:/ { print $$2 }' ${PKGNAME}.spec | sed -e 's|%.*$$||g')

PREFIX=/usr

all:

clean:
	-rm *.tar.gz rpmhelper/*.pyc
	-rm -r dist MANIFEST
	python setup.py -q clean --all

install: all
	python setup.py install --root=$(DESTDIR)

archive:
	@git archive --format=tar --prefix=${PKGNAME}-${VERSION}/ HEAD \
		| gzip > ${PKGNAME}-$(VERSION).tar.gz
	@echo "The archive is in ${PKGNAME}-$(VERSION).tar.gz"
