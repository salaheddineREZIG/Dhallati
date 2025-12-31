--.schema
----
--DELETE FROM items;
--DELETE FROM item_images;
--DELETE FROM reports;
--DELETE FROM users;
--DELETE FROM audit_logs;
--DELETE FROM notifications;
--DELETE FROM claims;
--DELETE FROM verification_questions;


--
SELECT * FROM users;
SELECT * FROM audit_logs;
----\
--SELECT * FROM users;
----
------ Insert main categories into the categories table
----
--INSERT INTO categories (name, description) VALUES
--('Electronics', 'Devices and accessories.'),
--('Clothing', 'Apparel and accessories.'),
--('Books & Stationery', 'Textbooks, notebooks, and writing supplies.'),
--('Bags & Wallets', 'Bags, purses, wallets, and related items.'),
--('Keys', 'Various types of keys.'),
--('ID Cards & Documents', 'Personal identification and important documents.'),
--('Sports Equipment', 'Equipment and accessories for sports activities.'),
--('Miscellaneous', 'Other items not fitting into the above categories.');
--
--INSERT OR IGNORE INTO locations (name, description) VALUES
--('Library', 'Central library'),
--('Science Faculty', ' Science departments'),
--('Science Building', 'Science laboratories and classrooms'),
--('Engineering Building', 'Engineering departments'),
--('Main Cafeteria', 'Primary dining hall'),
--('Sports Complex', 'Gymnasium and sports facilities'),
--('Parking Lot A', 'Main entrance parking lot'),
--('Parking Lot B', 'parking lot facing the Science Faculty'),
--('Parking Lot C', 'parking lot near the Sports Complex'),
--('Administration Building', 'University administration offices'),
--('Computer Lab', 'Main computer laboratory'),
--('Auditorium Section', 'Large event '),
--('Dormitory A', 'North residence hall'),
--('Dormitory B', 'South residence hall');
SELECT * FROM items;
SELECT * FROM reports;
SELECT * FROM item_images;
SELECT * FROM notifications;
SELECT * FROM verification_questions; 
SELECT * FROM claims;
------.tables
----