%{!?python_sitearch: %define python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

Summary: Helper scripts for rpm.
Name: rpmhelper
URL: http://www.linuxfans.org
Version: 0.02
Release: 2%{?dist}
Source0: %{name}-%{version}.tar.gz
License: GPL
Group: Application/Tools
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
Requires: python

%description
rpmhelper is a set of scripts and libs aimed for ease management of
rpm files.

%prep
%setup -q

%build
make

%install
rm -rf %{buildroot}
make DESTDIR=${RPM_BUILD_ROOT} install

#%find_lang %name

%clean
rm -rf %{buildroot}

#%files -f %{name}.lang
%files
%defattr(-,root,root,-)
%doc README ChangeLog COPYING
%dir %{python_sitearch}/rpmhelper
%{python_sitearch}/rpmhelper
%{_bindir}/rpm-diff
%{_bindir}/rpm-findold
%{_bindir}/rpm-findnewest
%{_bindir}/rpm-parsespec
%{_bindir}/mb-init
%{_bindir}/mb-prepare
%{_bindir}/mb-build
%{_bindir}/mb-pull-pkg
%{_bindir}/mb-push-pkg
%{_bindir}/mb-fetch-fcpkg

%changelog
* Tue Aug 21 2007 Levin Du <zsdjw@21cn.com> 0.02
- Add mb-init, mb-build, mb-prepare
- Add mb-pull-pkg, mb-push-pkg, mb-fetch-fcpkg
- Add rpm-parsespec
- Rename rpmdiff, rpmfindold to rpm-diff, rpm-findold
- Add rpm-findnewest

* Thu Aug  2 2007 Levin Du <zsdjw@21cn.com> 0.01
- First created.

