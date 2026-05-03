<?php

/**
 * Clinical Co-Pilot — validates the browser OpenEMR UI session (PHP session cookies).
 *
 * Load with $ignoreAuth so we return JSON instead of auth.inc redirect HTML, then
 * enforce session. Prefer AuthUtils::authCheckSession() (password hash matches DB);
 * if that fails but $_SESSION still holds a core clinician login, fall back to an
 * active-user DB check so hash-migration / edge cases do not block co-pilot.
 *
 * OAuth Bearer tokens are not PHP sessions; the agent uses Standard API routes for those.
 */

use OpenEMR\Common\Acl\AclExtended;
use OpenEMR\Common\Acl\AclMain;
use OpenEMR\Common\Auth\AuthUtils;
use OpenEMR\Common\Session\SessionUtil;

$ignoreAuth = true;
require_once dirname(__FILE__) . '/../globals.php';

// globals.php starts the session read-mostly (read_and_close). Re-bind to the OpenEMR= cookie
// with a writable session so AuthUtils sees the same data as the main app.
SessionUtil::switchToCoreSession($GLOBALS['webroot'] ?? '', false);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate');

$strictSession = AuthUtils::authCheckSession();
$fallbackSession = false;
if (!$strictSession) {
    if (
        !empty($_SESSION['authUserID'])
        && !empty($_SESSION['authUser'])
    ) {
        $row = privQuery(
            "SELECT `username`, `active` FROM `users` WHERE `id` = ?",
            [$_SESSION['authUserID']]
        );
        $fallbackSession = !empty($row)
            && !empty($row['active'])
            && ((string) $row['username'] === (string) $_SESSION['authUser']);
    }
}

if (!$strictSession && !$fallbackSession) {
    http_response_code(401);
    echo json_encode([
        'error' => 'unauthorized',
        'message' => 'No valid OpenEMR session',
    ]);
    exit;
}

$session = \OpenEMR\Common\Session\SessionWrapperFactory::getInstance()->getActiveSession();
$authUserID = $session->get('authUserID');
$authUser = $session->get('authUser');

if (empty($authUserID) || empty($authUser)) {
    http_response_code(401);
    echo json_encode([
        'error' => 'unauthorized',
        'message' => 'Session incomplete',
    ]);
    exit;
}

$groups = AclExtended::aclGetGroupTitles((string) $authUser);
if (!is_array($groups)) {
    $groups = [];
}
$groups = array_values($groups);

$isAdmin = AclMain::aclCheckCore('admin', 'users', '', (string) $authUser);
if ($isAdmin) {
    $hasAdminGroup = false;
    foreach ($groups as $g) {
        if (stripos((string) $g, 'admin') !== false) {
            $hasAdminGroup = true;
            break;
        }
    }
    if (!$hasAdminGroup) {
        $groups[] = 'Administrators';
    }
}

echo json_encode([
    'id' => (string) $authUserID,
    'username' => (string) $authUser,
    'groups' => $groups,
    'admin' => $isAdmin ? 1 : 0,
]);
