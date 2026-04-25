CREATE TABLE post (post_id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
# должности

CREATE TABLE employee (employee_id SERIAL PRIMARY KEY, surname TEXT NOT NULL, name TEXT NOT NULL, patronymic text,
  post_id INT REFERENCES post(post_id), phone VARCHAR(255));
# сотрудники

CREATE TABLE client (client_id SERIAL PRIMARY KEY, surname TEXT, name TEXT NOT NULL, patronymic text, phone VARCHAR(255), email TEXT);
# клиенты

CREATE TABLE payment_method (payment_method_id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
# методы оплаты

CREATE TABLE contact_method (contact_method_id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
# методы связи

CREATE TABLE service (service_id SERIAL PRIMARY KEY, name TEXT NOT NULL, service_price NUMERIC(10, 2) NOT NULL);
# услуги

CREATE TABLE order_info (order_info_id SERIAL PRIMARY KEY, order_id INT, service_id INT REFERENCES service(service_id), quantity INT);
# данные о покупке

CREATE TABLE orders (order_id SERIAL PRIMARY KEY, client_id INT REFERENCES client(client_id), payment_method_id INT REFERENCES payment_method(payment_method_id),
  date TIMESTAMP DEFAULT NOW(), total_sum NUMERIC(10, 2), contact_method_id INT REFERENCES contact_method(contact_method_id));
# все покупки

CREATE TABLE users (user_id SERIAL PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('owner', 'administrator', 'worker', 'accountant')), name TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
# пользователи бд


GRANT CONNECT ON DATABASE photo_studio TO owner_user, dba_user, accountant_user, worker_user;
GRANT USAGE ON SCHEMA public TO owner_user, dba_user, accountant_user, worker_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO owner_user;
GRANT TEMPORARY ON DATABASE photo_studio TO owner_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO owner_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO owner_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dba_user;
GRANT INSERT, UPDATE, DELETE ON post, employee, client, payment_method, contact_method, service, order_info, orders TO dba_user;
GRANT SELECT ON users TO dba_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dba_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dba_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO dba_user;
GRANT SELECT ON service, payment_method, client, post, employee, contact_method TO worker_user;
GRANT SELECT, INSERT ON orders, order_info, client TO worker_user;
GRANT UPDATE ON client TO worker_user;
GRANT USAGE, SELECT ON orders_order_id_seq, order_info_order_info_id_seq, client_client_id_seq TO worker_user;
GRANT SELECT ON orders, order_info, service, client, payment_method, employee TO accountant_user;
GRANT SELECT ON orders_order_id_seq, order_info_order_info_id_seq TO accountant_user;
