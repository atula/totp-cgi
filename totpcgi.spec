%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%global selinux_policyver %(%{__sed} -e 's,.*selinux-policy-\\([^/]*\\)/.*,\\1,' /usr/share/selinux/devel/policyhelp || echo 0.0.0)

%global selinux_variants mls strict targeted

%define totpcgiuser     totpcgi
%define totpcgiprovuser totpcgiprov

Name:		totpcgi
Version:	0.5.0
Release:	1%{?dist}
Summary:	A centralized totp solution based on google-authenticator

License:	GPLv2+
URL:		https://github.com/mricon/totp-cgi
Source0:	%{name}-%{version}.tar.gz

BuildArch:	noarch

BuildRequires: checkpolicy, selinux-policy-devel, hardlink
BuildRequires: /usr/share/selinux/devel/policyhelp

Requires:	httpd, mod_ssl
Requires:   python-totpcgi = %{version}-%{release}


%description
A CGI/FCGI application to centralize google-authenticator deployments.


%package -n python-totpcgi
Summary:    Python libraries required for totpcgi
Requires:   py-bcrypt, python-pyotp, python-crypto, python-passlib

%description -n python-totpcgi
This package includes the Python libraries required for totpcgi and
totpcgi-provisioning.


%package provisioning
Summary:    CGI for Google Authenticator provisioning using totpcgi
Requires:   python-totpcgi = %{version}-%{release}
Requires:   httpd, mod_ssl, python-qrcode

%description provisioning
This package provides the CGI for provisioning Google Authenticator tokens
used by totpcgi.


%package selinux
Summary:    SELinux policies for totpcgi
Requires:   %{name} = %{version}-%{release}
Requires:   selinux-policy >= %{selinux_policyver}
Requires(post):   /usr/sbin/semodule, /sbin/restorecon, /sbin/fixfiles
Requires(postun): /usr/sbin/semodule, /sbin/restorecon, /sbin/fixfiles

%description selinux
This package includes SELinux policy for totpcgi and totpcgi-provisioning.


%prep
%setup -q


%build
%{__python} setup.py build
pushd selinux
for selinuxvariant in %{selinux_variants}
do
  make NAME=${selinuxvariant} -f /usr/share/selinux/devel/Makefile
  mv totpcgi.pp totpcgi.pp.${selinuxvariant}
  make NAME=${selinuxvariant} -f /usr/share/selinux/devel/Makefile clean
done
popd


%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

# Install config files
mkdir -p -m 0750  %{buildroot}%{_sysconfdir}/totpcgi
mkdir -p -m 0750 \
    %{buildroot}%{_sysconfdir}/totpcgi/totp \
    %{buildroot}%{_sysconfdir}/totpcgi/templates
install -m 0640 conf/*.conf %{buildroot}%{_sysconfdir}/totpcgi/
install -m 0640 conf/templates/*.html %{buildroot}%{_sysconfdir}/totpcgi/templates/

# Create the state directory
mkdir -p -m 0700 %{buildroot}%{_localstatedir}/lib/totpcgi

# Create the CGI dirs
mkdir -p -m 0751 \
    %{buildroot}%{_localstatedir}/www/totpcgi \
    %{buildroot}%{_localstatedir}/www/totpcgi-provisioning

# Install the web files
install -m 0550 cgi/totp.cgi \
    %{buildroot}%{_localstatedir}/www/totpcgi/index.cgi
install -m 0550 cgi/provisioning.cgi \
    %{buildroot}%{_localstatedir}/www/totpcgi-provisioning/index.cgi
install -m 0644 cgi/*.css \
    %{buildroot}%{_localstatedir}/www/totpcgi-provisioning/

# Install the httpd config files
mkdir -p -m 0755 %{buildroot}%{_sysconfdir}/httpd/conf.d
install -m 0644 contrib/vhost-totpcgi.conf \
    %{buildroot}%{_sysconfdir}/httpd/conf.d/totpcgi.conf
install -m 0644 contrib/vhost-totpcgi-provisioning.conf \
    %{buildroot}%{_sysconfdir}/httpd/conf.d/totpcgi-provisioning.conf

# Install totpprov script and manpage
mkdir -p -m 0755 %{buildroot}%{_bindir}
install -m 0755 contrib/totpprov.py %{buildroot}%{_bindir}/totpprov
mkdir -p -m 0755 %{buildroot}%{_mandir}
install -m 0644 contrib/totpprov.5 %{buildroot}%{_mandir}/5/

# Install SELinux files
for selinuxvariant in %{selinux_variants}
do
  install -d %{buildroot}%{_datadir}/selinux/${selinuxvariant}
  install -p -m 644 selinux/totpcgi.pp.${selinuxvariant} \
    %{buildroot}%{_datadir}/selinux/${selinuxvariant}/totpcgi.pp
done
/usr/sbin/hardlink -cv %{buildroot}%{_datadir}/selinux


%pre
# We always add both the totpcgi and totpcgi-provisioning user
/usr/sbin/useradd -c "Totpcgi user" \
	-M -s /sbin/nologin -d /var/lib/totpcgi %{totpcgiuser} 2> /dev/null || :
/usr/sbin/useradd -c "Totpcgi provisioning user" \
	-M -s /sbin/nologin -d /etc/totpcgi %{totpcgiprovuser} 2> /dev/null || :


%post selinux
for selinuxvariant in %{selinux_variants}
do
  /usr/sbin/semodule -s ${selinuxvariant} -i \
    %{_datadir}/selinux/${selinuxvariant}/totpcgi.pp &> /dev/null || :
done
/sbin/fixfiles -R totpcgi restore || :

%postun selinux
if [ $1 -eq 0 ] ; then
  for selinuxvariant in %{selinux_variants}
  do
    /usr/sbin/semodule -s ${selinuxvariant} -r totpcgi &> /dev/null || :
  done
  /sbin/fixfiles -R totpcgi restore || :
fi


%files
%doc README.rst INSTALL.rst
%doc contrib
%doc cgi/totp.fcgi
%dir %attr(-, %{totpcgiprovuser}, %{totpcgiuser}) %{_sysconfdir}/totpcgi
%dir %attr(-, %{totpcgiprovuser}, %{totpcgiuser}) %{_sysconfdir}/totpcgi/totp
%dir %attr(-, %{totpcgiuser}, %{totpcgiuser}) %{_localstatedir}/www/totpcgi
%attr(-, %{totpcgiuser}, %{totpcgiuser}) %{_localstatedir}/www/totpcgi/*.cgi
%config(noreplace) %attr(-, -, %{totpcgiuser}) %{_sysconfdir}/totpcgi/totpcgi.conf
%config(noreplace) %{_sysconfdir}/httpd/conf.d/totpcgi.conf
%attr(-, %{totpcgiuser}, %{totpcgiuser}) %{_localstatedir}/lib/totpcgi

%files -n python-totpcgi
%doc COPYING
%{python_sitelib}/*
%dir %attr(-, %{totpcgiprovuser}, %{totpcgiuser}) %{_sysconfdir}/totpcgi
%dir %attr(-, %{totpcgiprovuser}, %{totpcgiuser}) %{_sysconfdir}/totpcgi/totp
%config(noreplace) %attr(-, -, %{totpcgiprovuser}) %{_sysconfdir}/totpcgi/provisioning.conf
%{_bindir}/*
%{_mandir}/*/*

%files provisioning
%dir %attr(-, %{totpcgiprovuser}, %{totpcgiprovuser}) %{_localstatedir}/www/totpcgi-provisioning
%attr(-, %{totpcgiprovuser}, %{totpcgiprovuser}) %{_localstatedir}/www/totpcgi-provisioning/*.cgi
%config(noreplace) %{_localstatedir}/www/totpcgi-provisioning/*.css
%config(noreplace) %{_sysconfdir}/httpd/conf.d/totpcgi-provisioning.conf
%dir %attr(-, -, %{totpcgiprovuser}) %{_sysconfdir}/totpcgi/templates
%config(noreplace) %attr(-, -, %{totpcgiprovuser}) %{_sysconfdir}/totpcgi/templates/*.html

%files selinux
%defattr(-,root,root,0755)
%doc selinux/*.{fc,if,sh,te}
%{_datadir}/selinux/*/totpcgi.pp


%changelog
* Thu May 24 2012 Konstantin Ryabitsev <mricon@kernel.org> - 0.5.0-1
- Split into more packages: totpcgi, python-totpcgi, totpcgi-provisioning, totpcgi-selinux

* Tue May 08 2012 Konstantin Ryabitsev <mricon@kernel.org> - 0.4.0-1
- Update to 0.4.0, which adds encrypted-secret functionality.
- Require python-crypto and python-passlib

* Fri May 04 2012 Konstantin Ryabitsev <mricon@kernel.org> - 0.3.1-3
- Package SELinux using Fedora's guidelines.
- Add contrib dir in its entirety.
- Use config(noreplace).

* Tue May 01 2012 Andrew Grimberg <agrimberg@linuxfoundation.org> - 0.3.1-2
- Exceptions on bad passwords to LDAP
- Config for CA cert to use for verification
- PostgreSQL pincode & secrets backends

* Thu Apr 12 2012 Andrew Grimberg <agrimberg@linuxfoundation.org> - 0.3.0-1
- Bump version number
- Split backend system

* Wed Apr 11 2012 Andrew Grimberg <agrimberg@linuxfoundation.org> - 0.2.0-4
- Add in pincode.py script

* Mon Mar 26 2012 Andrew Grimberg <agrimberg@linuxfoundation.org> - 0.2.0-3
- Fix path perms for /var/www/totpcgi so that apache can chdir
- Reduce perms on /var/www/totpcgi/totp.cgi to bare minimum

* Fri Mar 23 2012 Konstantin Ryabitsev <mricon@kernel.org> - 0.2.0-2
- Update to better match Fedora's spec standards.

* Wed Mar 21 2012 Andrew Grimberg <agrimberg@linuxfoundation.org> - 0.2.0-1
- Initial spec file creation and packaging