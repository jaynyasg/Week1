#!/bin/sh
set -e

OPENEMR_SH=/var/www/localhost/htdocs/openemr/openemr.sh
if [ -f "$OPENEMR_SH" ]; then
  python3 - <<'PY'
from pathlib import Path
path = Path('/var/www/localhost/htdocs/openemr/openemr.sh')
text = path.read_text()

# Patch 1: guard the top-level require_once so a missing sqlconf.php does not
# crash the script with a PHP fatal before the auto-installer can run.
old = 'CONFIG=$(php -r "require_once(\'/var/www/localhost/htdocs/openemr/sites/default/sqlconf.php\'); echo \\$config;")'
new = '''if [ -f /var/www/localhost/htdocs/openemr/sites/default/sqlconf.php ]; then
  CONFIG=$(php -r "require_once('/var/www/localhost/htdocs/openemr/sites/default/sqlconf.php'); echo \$config;")
else
  CONFIG=0
fi'''
if old in text:
    text = text.replace(old, new)

# Patch 2: add -r (no-run-if-empty) to xargs invocations that chmod the
# tree. On a fresh volume sites/default/documents has no entries, so
# busybox xargs would invoke chmod with no args and exit 123, killing the
# container in a restart loop right after auto-install.
text = text.replace('xargs -0 -P', 'xargs -0 -r -P')

path.write_text(text)
PY
  chmod +x "$OPENEMR_SH"
  exec "$OPENEMR_SH" "$@"
fi

exec "$OPENEMR_SH" "$@"
