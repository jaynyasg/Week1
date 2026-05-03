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

  # openemr.conf defines <VirtualHost *:80> — Apache uses only the FIRST
  # matching VirtualHost, so a separate conf file's VirtualHost *:80 block is
  # silently ignored. Instead, we inject the proxy directives directly into the
  # existing VirtualHost *:80 block using Python (available in this image).
  openemr_conf="/etc/apache2/conf.d/openemr.conf"
  if [ ! -f "$openemr_conf" ]; then
    echo "clinical-copilot: $openemr_conf not found; /agent proxy not configured" >&2
    return 0
  fi

  python3 - "$openemr_conf" "$agent_url" <<'PY'
import sys, re
conf_path, agent_url = sys.argv[1], sys.argv[2]
text = open(conf_path).read()

marker = "# clinical-copilot-proxy-injected"
if marker in text:
    print("clinical-copilot: proxy already injected into", conf_path)
    sys.exit(0)

injection = """
    {marker}
    <IfModule proxy_module>
        ProxyPreserveHost On
        ProxyPass /agent {agent_url}/agent
        ProxyPassReverse /agent {agent_url}/agent
    </IfModule>

    Alias /interface/copilot /var/www/localhost/htdocs/openemr/interface/copilot
    <Directory "/var/www/localhost/htdocs/openemr/interface/copilot">
        AllowOverride None
        Require all granted
        Options FollowSymLinks
    </Directory>
""".format(marker=marker, agent_url=agent_url)

# Insert before the first </VirtualHost> closing tag (the *:80 block)
new_text = re.sub(r'(</VirtualHost>)', injection + r'\1', text, count=1)
open(conf_path, 'w').write(new_text)
print("clinical-copilot: injected proxy into", conf_path, "->", agent_url + "/agent")
PY
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
