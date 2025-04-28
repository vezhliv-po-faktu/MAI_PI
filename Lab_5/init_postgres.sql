CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL
);

INSERT INTO users (username, password) VALUES ('admin', '$2b$12$b7V20JcpA4/VH9Nzp4mB.eZBWyrVsCxlyGihynAQh2Z802Jp1d61S');

CREATE INDEX username_idx ON users(username);