#!/bin/sh
# Best-effort enable Apache mod_proxy (+ rewrite) for Clinical Co-Pilot reverse proxy.
# OpenEMR base images differ (Debian a2enmod vs Alpine httpd.conf); this script is tolerant.
set -e

if command -v a2enmod >/dev/null 2>&1; then
  a2enmod proxy proxy_http rewrite 2>/dev/null || true
  echo "enable-apache-proxy-modules: a2enmod proxy proxy_http rewrite"
  exit 0
fi

if [ -f /etc/apache2/httpd.conf ]; then
  # Alpine httpd: uncomment common module lines if present.
  for pat in \
    's/^#\(LoadModule proxy_module\)/\1/' \
    's/^#\(LoadModule proxy_http_module\)/\1/' \
    's/^#\(LoadModule rewrite_module\)/\1/'; do
    sed -i "$pat" /etc/apache2/httpd.conf 2>/dev/null || true
  done
  echo "enable-apache-proxy-modules: patched /etc/apache2/httpd.conf (Alpine-style)"
  exit 0
fi

if [ -f /etc/httpd/conf/httpd.conf ]; then
  sed -i 's/^#\(LoadModule proxy_module\)/\1/' /etc/httpd/conf/httpd.conf 2>/dev/null || true
  sed -i 's/^#\(LoadModule proxy_http_module\)/\1/' /etc/httpd/conf/httpd.conf 2>/dev/null || true
  echo "enable-apache-proxy-modules: patched /etc/httpd/conf/httpd.conf (best-effort)"
  exit 0
fi

echo "enable-apache-proxy-modules: no known httpd layout — mod_proxy may need manual enable"
exit 0
