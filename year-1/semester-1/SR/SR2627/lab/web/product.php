<?php
// SQL injection target for role 4. Two unsafe sinks on purpose:
//   /product.php?id=1          -> numeric context  (UNION SELECT ...)
//   /product.php?q=mug         -> string context   (' OR '1'='1)
// The point of the lab is that the firewall (role 4's DPI) can see the
// payload on the wire; the app itself is intentionally broken.
declare(strict_types=1);
require __DIR__ . '/db.php';

header('Content-Type: text/html; charset=utf-8');
$db = db_connect();

$id = $_GET['id'] ?? null;
$q  = $_GET['q'] ?? null;

if ($q !== null) {
    $sql = "SELECT id, name, description, price FROM products WHERE name LIKE '%$q%'";
} else {
    $id = $id ?? '1';
    $sql = "SELECT id, name, description, price FROM products WHERE id = $id";
}

echo "<!doctype html><html><head><meta charset='utf-8'><title>Product</title></head><body>";
echo "<p><a href='/'>back</a></p>";
echo "<pre>query: " . htmlspecialchars($sql) . "</pre>";

try {
    $result = $db->query($sql);
    echo "<table border='1' cellpadding='6'><tr><th>id</th><th>name</th><th>description</th><th>price</th></tr>";
    while ($row = $result->fetch_assoc()) {
        echo "<tr>";
        foreach ($row as $value) {
            echo "<td>" . htmlspecialchars((string) $value) . "</td>";
        }
        echo "</tr>";
    }
    echo "</table>";
} catch (Throwable $e) {
    // Verbose on purpose: the error text makes SQLi feedback obvious.
    http_response_code(500);
    echo "<pre>sql error: " . htmlspecialchars($e->getMessage()) . "</pre>";
}

$db->close();
echo "</body></html>";
