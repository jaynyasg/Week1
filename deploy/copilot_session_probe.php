<?php

/**
 * Clinical Co-Pilot — validates the browser OpenEMR UI session (PHP session cookies).
 *
 * Load with $ignoreAuth so we return JSON instead of auth.inc redirect HTML, then
 * enforce session. Prefer AuthUtils::authCheckSession() (password hash matches DB);
 * if that fails but $_SESSION still holds a core clinician login, fall back to an
 * active-user DB check so hash-migration / edge cases do not block co-pilot.
 *
 * Group names come from phpGACL tables via SQL. Avoid AclExtended/AclMain here:
 * initializing Gacl/GaclApi under $ignoreAuth can fatally error while normal pages work.
 *
 * OAuth Bearer tokens are not PHP sessions; the agent uses Standard API routes for those.
 */

use OpenEMR\Common\Auth\AuthUtils;

$ignoreAuth = true;
// This file lives in interface/ (same dir as globals.php), not interface/login/.
require_once dirname(__FILE__) . '/globals.php';

/**
 * Group display names (gacl_aro_groups.name) for a login — mirrors AclExtended::aclGetGroupTitles output shape.
 *
 * @return list<string>
 */
function copilot_probe_acl_group_names(string $username): array
{
    $names = [];
    $sql = "
        SELECT DISTINCT gag.name AS grp_name
        FROM gacl_aro AS garo
        INNER JOIN gacl_groups_aro_map AS gam ON garo.id = gam.aro_id
        INNER JOIN gacl_aro_groups AS gag ON gam.group_id = gag.id
        WHERE garo.section_value = 'users'
          AND garo.value = ?
        ORDER BY grp_name
    ";
    $res = sqlStatement($sql, [$username]);
    while ($row = sqlFetchArray($res)) {
        if (!empty($row['grp_name'])) {
            $names[] = $row['grp_name'];
        }
    }
    return array_values(array_unique($names));
}

/**
 * Approximate admin/users ACL using group membership (Administrators and similar).
 */
function copilot_probe_user_is_admin_like(array $groups): bool
{
    foreach ($groups as $g) {
        $gl = strtolower((string) $g);
        if (stripos($gl, 'admin') !== false) {
            return true;
        }
    }
    return false;
}

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

$authUserID = $_SESSION['authUserID'] ?? null;
$authUser = $_SESSION['authUser'] ?? null;

if (empty($authUserID) || empty($authUser)) {
    http_response_code(401);
    echo json_encode([
        'error' => 'unauthorized',
        'message' => 'Session incomplete',
    ]);
    exit;
}

$groups = copilot_probe_acl_group_names((string) $authUser);
$isAdmin = copilot_probe_user_is_admin_like($groups);

echo json_encode([
    'id' => (string) $authUserID,
    'username' => (string) $authUser,
    'groups' => $groups,
    'admin' => $isAdmin ? 1 : 0,
]);
