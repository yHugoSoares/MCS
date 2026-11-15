<?php
// Deliberately vulnerable demo app (TP4 lab, isolated network only).
declare(strict_types=1);
require __DIR__ . '/db.php';

$db = db_connect();
$count = $db->query('SELECT COUNT(*) AS n FROM products')->fetch_assoc()['n'];
$db->close();
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>TP4 protected service</title>
    <style>
        body { font-family: ui-monospace, monospace; margin: 3rem auto; max-width: 40rem; }
        code { background: #eee; padding: 0 .25rem; }
        .warn { border: 2px solid #c00; padding: .75rem 1rem; background: #fff5f5; }
    </style>
</head>
<body>
    <h1>TP4 protected service</h1>
    <p class="warn">Intentionally vulnerable. Reachable only from the isolated lab.</p>
    <p><?= (int) $count ?> products in the catalogue.</p>
    <ul>
        <li><a href="/product.php?id=1">Product 1</a></li>
        <li><a href="/product.php?id=2">Product 2</a></li>
        <li><a href="/product.php?q=mug">Search "mug"</a></li>
        <li><a href="/healthz.php">Health check</a></li>
    </ul>
</body>
</html>
