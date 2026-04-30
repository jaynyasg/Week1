#!/bin/sh
set -e

OPENEMR_SH=/var/www/localhost/htdocs/openemr/openemr.sh
if [ -f "$OPENEMR_SH" ]; then
  python3 - <<'PY'
from pathlib import Path
path = Path('/var/www/localhost/htdocs/openemr/openemr.sh')
text = path.read_text()
old = 'CONFIG=$(php -r "require_once(\'/var/www/localhost/htdocs/openemr/sites/default/sqlconf.php\'); echo \\$config;")'
new = '''if [ -f /var/www/localhost/htdocs/openemr/sites/default/sqlconf.php ]; then
  CONFIG=$(php -r "require_once('/var/www/localhost/htdocs/openemr/sites/default/sqlconf.php'); echo \$config;")
else
  CONFIG=0
fi'''
if old in text:
    path.write_text(text.replace(old, new))
PY
  chmod +x "$OPENEMR_SH"
  exec "$OPENEMR_SH" "$@"
fi

exec "$OPENEMR_SH" "$@"
