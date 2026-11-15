-- Intentionally small, intentionally naive schema. Lab only.
-- Role 4 attacks this through the web app (SQL injection).

CREATE TABLE IF NOT EXISTS users (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64)  NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,        -- plaintext on purpose: demo target
    role     VARCHAR(16)  NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS products (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(128)  NOT NULL,
    description VARCHAR(255)  NOT NULL,
    price       DECIMAL(10, 2) NOT NULL
);

INSERT INTO users (username, password, role) VALUES
    ('alice', 'alice123', 'user'),
    ('bob',   'bob123',   'user'),
    ('admin', 's3cr3t-admin', 'admin');

INSERT INTO products (name, description, price) VALUES
    ('Firewall Mug',  'Holds coffee, blocks distractions', 9.90),
    ('Packet Plush',  'Squeezable TCP segment',            14.50),
    ('Stateful Tee',  'Remembers every connection',        19.00);
