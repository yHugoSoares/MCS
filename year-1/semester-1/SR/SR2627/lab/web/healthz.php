<?php
// Availability endpoint used by: docker healthcheck, the legitimate traffic
// generator and the attacker's "is the service still up?" checks.
declare(strict_types=1);
require __DIR__ . '/db.php';

header('Content-Type: text/plain; charset=utf-8');

try {
    $db = db_connect();
    $db->query('SELECT 1');
    $db->close();
    http_response_code(200);
    echo "ok\n";
} catch (Throwable $e) {
    http_response_code(503);
    echo "degraded: database unavailable\n";
}
