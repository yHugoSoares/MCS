<?php
// Lab-only database helper. Credentials come from the container environment.
declare(strict_types=1);

function db_connect(): mysqli
{
    $host = getenv('LAB_DB_HOST') ?: '10.9.1.3';
    $name = getenv('LAB_DB_NAME') ?: 'labdb';
    $user = getenv('LAB_DB_USER') ?: 'labuser';
    $pass = getenv('LAB_DB_PASS') ?: 'labpass';

    mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
    $db = new mysqli($host, $user, $pass, $name, 3306);
    $db->set_charset('utf8mb4');
    return $db;
}
