#!/bin/sh
set -e

SITES_DIR=/var/www/localhost/htdocs/openemr/sites
TEMPLATE_DIR=/swarm-pieces/sites

# Seed the sites/ tree from the image template if config.php is missing.
# Fly volumes mount empty (unlike Docker named volumes which auto-copy
# image content), and the upstream rsync of /swarm-pieces only runs when
# SWARM_MODE=yes — so on Fly, the per-site templates (config.php and
# friends) never land in the volume and globals.php throws a fatal
# requiring config.php.
if [ ! -f "$SITES_DIR/default/config.php" ] && [ -d "$TEMPLATE_DIR" ]; then
  echo "Seeding $SITES_DIR from $TEMPLATE_DIR (fresh volume detected)"
  # Iterate explicitly so we never clobber an existing sqlconf.php or
  # documents/ tree if a partial install already wrote them.
  for entry in "$TEMPLATE_DIR"/*; do
    name=$(basename "$entry")
    if [ ! -e "$SITES_DIR/$name" ]; then
      cp -r "$entry" "$SITES_DIR/$name"
    fi
  done
fi

# Ensure sites/ is owned by apache. Fly mounts the volume as root:root,
# and the upstream startup chmods to 500/400 without chowning — so
# apache (the httpd user) ends up unable to traverse sites/. Run chown
# in the background so Apache can start (and pass health checks) while
# ownership is being fixed. openemr.sh re-chowns individual files it
# touches, so partial ownership is safe during the startup window.
if [ -d "$SITES_DIR" ]; then
  chown -R apache:root "$SITES_DIR" &
fi

COPILOT_STATIC=/var/www/localhost/htdocs/openemr/interface/copilot
if [ -d "$COPILOT_STATIC" ]; then
  chown -R apache:root "$COPILOT_STATIC" &
fi

# Apache: reverse-proxy /agent → FastAPI agent on Fly 6PN; serve SPA under /interface/copilot/.
# CLINICAL_AGENT_INTERNAL_URL is set in fly.toml [env] (e.g. http://clinical-agent-scaffold.internal:8080).
write_copilot_apache_conf() {
  agent_url="${CLINICAL_AGENT_INTERNAL_URL:-http://clinical-agent-scaffold.internal:8080}"
  agent_url="${agent_url%/}"
  conf=""
  for dir in /etc/apache2/conf-enabled /etc/apache2/conf.d /etc/httpd/conf.d; do
    if [ -d "$dir" ]; then
      conf="$dir/99-clinical-copilot.conf"
      break
    fi
  done
  if [ -z "$conf" ]; then
    echo "clinical-copilot: no apache conf.d found; /agent proxy not configured" >&2
    return 0
  fi
  # Proxy and copilot alias must live inside a <VirtualHost *:80> block because
  # openemr.conf already defines <VirtualHost *:80>, making the global context
  # irrelevant for port-80 requests. Apache merges multiple VirtualHost blocks
  # for the same address:port, so adding a second block here is safe.
  {
    echo "<VirtualHost *:80>"
    echo "    <IfModule mod_proxy.c>"
    echo "        ProxyPreserveHost On"
    echo "        ProxyPass /agent ${agent_url}/agent"
    echo "        ProxyPassReverse /agent ${agent_url}/agent"
    echo "    </IfModule>"
    echo ""
    echo "    Alias /interface/copilot /var/www/localhost/htdocs/openemr/interface/copilot"
    echo "    <Directory \"/var/www/localhost/htdocs/openemr/interface/copilot\">"
    echo "        AllowOverride None"
    echo "        Require all granted"
    echo "        Options FollowSymLinks"
    echo "        <IfModule mod_rewrite.c>"
    echo "            RewriteEngine On"
    echo "            RewriteBase /interface/copilot/"
    echo "            RewriteRule ^index\\.html\$ - [L]"
    echo "            RewriteCond %{REQUEST_FILENAME} !-f"
    echo "            RewriteCond %{REQUEST_FILENAME} !-d"
    echo "            RewriteRule . index.html [L]"
    echo "        </IfModule>"
    echo "    </Directory>"
    echo "</VirtualHost>"
  } >"$conf"
  echo "clinical-copilot: wrote $conf (proxy -> ${agent_url}/agent)"
}

write_copilot_apache_conf

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
