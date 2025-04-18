-- Mevcut tabloları temizleme (eğer varsa)
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

-- Kategoriler tablosu
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Ürünler tablosu
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category_id INT REFERENCES categories(category_id),
    unit_price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL,
    description TEXT
);

-- Müşteriler tablosu
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    registration_date DATE DEFAULT CURRENT_DATE
);

-- Siparişler tablosu
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('Beklemede', 'Onaylandı', 'Kargoda', 'Teslim Edildi', 'İptal'))
);

-- Sipariş detayları tablosu
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    product_id INT REFERENCES products(product_id),
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(5, 2) DEFAULT 0.00
);

-- İndeksler
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);



-- Kategoriler
INSERT INTO categories (category_name, description) VALUES
('Elektronik', 'Bilgisayar, telefon ve elektronik cihazlar'),
('Giyim', 'Erkek, kadın ve çocuk giyim ürünleri'),
('Kitap', 'Kitaplar ve e-kitaplar'),
('Ev & Yaşam', 'Ev dekorasyon ve yaşam ürünleri'),
('Spor & Outdoor', 'Spor malzemeleri ve outdoor ürünler');

-- Ürünler
INSERT INTO products (product_name, category_id, unit_price, stock_quantity, description) VALUES
-- Elektronik
('Akıllı Telefon Pro', 1, 12999.99, 50, 'En yeni model akıllı telefon'),
('Ultra HD Televizyon', 1, 7499.50, 30, '65 inç Ultra HD televizyon'),
('Dizüstü Bilgisayar', 1, 15999.99, 25, 'Güçlü işlemcili dizüstü bilgisayar'),
('Bluetooth Kulaklık', 1, 1299.99, 100, 'Kablosuz bluetooth kulaklık'),
('Akıllı Saat', 1, 2499.50, 45, 'Spor ve sağlık takip özellikli akıllı saat'),
('Deri Ceket', 2, 999.99, 20, 'Hakiki deri erkek ceket'),
('Spor Ayakkabı', 2, 599.50, 60, 'Hafif ve rahat koşu ayakkabısı'),
('Kış Montu', 2, 1299.99, 40, 'Su geçirmez kış montu'),
('Kot Pantolon', 2, 399.50, 75, 'Yüksek bel kadın kot pantolon'),
('Pamuklu Tişört', 2, 129.99, 200, 'Temel pamuklu tişört, çeşitli renklerde'),
('Suç ve Ceza', 3, 65.00, 100, 'Fyodor Dostoyevski klasik roman'),
('Yapay Zeka: Giriş', 3, 120.50, 50, 'Yapay zeka teknolojilerine giriş kitabı'),
('Dünyanın Tarihi', 3, 85.75, 40, 'Kapsamlı dünya tarihi ansiklopedisi'),
('Modern Psikoloji', 3, 95.00, 30, 'Güncel psikoloji araştırmaları'),
('Finansal Bağımsızlık', 3, 75.25, 60, 'Kişisel finans ve yatırım rehberi'),
('Akıllı Ev Asistanı', 4, 899.50, 35, 'Sesle kontrol edilebilir akıllı ev asistanı'),
('Yorganlar', 4, 499.99, 40, 'Dört mevsim mikro fiber yorgan'),
('Kahve Makinesi', 4, 1599.50, 25, 'Otomatik espresso ve kahve makinesi'),
('Yemek Takımı', 4, 799.75, 20, '24 parça porselen yemek takımı'),
('LED Avize', 4, 1299.00, 15, 'Modern tasarımlı LED avize'),
('Koşu Bandı', 5, 5999.99, 10, 'Katlanabilir ev tipi koşu bandı'),
('Yoga Matı', 5, 199.50, 100, 'Kaymaz yüzeyli profesyonel yoga matı'),
('Dağ Bisikleti', 5, 3999.75, 15, '21 vites dağ bisikleti'),
('Kamp Çadırı', 5, 899.00, 25, '4 kişilik su geçirmez kamp çadırı'),
('Trekking Botu', 5, 799.50, 30, 'Su geçirmez trekking ve dağcılık botu');

-- Müşteriler
INSERT INTO customers (first_name, last_name, email, phone, address) VALUES
('Ali', 'Yılmaz', 'ali.yilmaz@email.com', '5551234567', 'Kadıköy, İstanbul'),
('Ayşe', 'Kaya', 'ayse.kaya@email.com', '5559876543', 'Çankaya, Ankara'),
('Mehmet', 'Demir', 'mehmet.demir@email.com', '5553456789', 'Konak, İzmir'),
('Fatma', 'Öztürk', 'fatma.ozturk@email.com', '5557890123', 'Melikgazi, Kayseri'),
('Ahmet', 'Şahin', 'ahmet.sahin@email.com', '5552345678', 'Nilüfer, Bursa'),
('Zeynep', 'Çelik', 'zeynep.celik@email.com', '5558765432', 'Muratpaşa, Antalya'),
('Hüseyin', 'Arslan', 'huseyin.arslan@email.com', '5554567890', 'Seyhan, Adana'),
('Elif', 'Güneş', 'elif.gunes@email.com', '5550987654', 'Selçuklu, Konya'),
('Mustafa', 'Aydın', 'mustafa.aydin@email.com', '5556789012', 'Atakum, Samsun'),
('Seda', 'Yıldız', 'seda.yildiz@email.com', '5553210987', 'Osmangazi, Bursa');

-- Siparişler
INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
(1, '2023-10-15 10:30:00', 13599.99, 'Teslim Edildi'),
(2, '2023-10-17 14:45:00', 599.50, 'Teslim Edildi'),
(3, '2023-10-20 09:15:00', 17299.98, 'Kargoda'),
(4, '2023-10-22 16:20:00', 1299.49, 'Teslim Edildi'),
(5, '2023-10-25 11:05:00', 3999.75, 'Onaylandı'),
(6, '2023-10-28 15:30:00', 899.00, 'Beklemede'),
(7, '2023-11-01 08:45:00', 8698.50, 'Onaylandı'),
(8, '2023-11-05 13:10:00', 265.75, 'Kargoda'),
(9, '2023-11-10 17:25:00', 2099.49, 'Teslim Edildi'),
(1, '2023-11-15 10:00:00', 7499.50, 'Onaylandı'),
(2, '2023-11-18 14:30:00', 1299.99, 'Beklemede'),
(4, '2023-11-22 09:45:00', 799.50, 'Onaylandı');

-- Sipariş Detayları
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount) VALUES
(1, 1, 1, 12999.99, 0.00),
(1, 4, 1, 1299.99, 5.00),
(2, 7, 1, 599.50, 0.00),
(3, 3, 1, 15999.99, 0.00),
(3, 5, 1, 2499.50, 6.00),
(4, 10, 10, 129.99, 0.00),
(5, 23, 1, 3999.75, 0.00),
(6, 24, 1, 899.00, 0.00),
(7, 2, 1, 7499.50, 0.00),
(7, 9, 3, 399.50, 0.00),
(8, 11, 2, 65.00, 0.00),
(8, 13, 1, 85.75, 0.00),
(8, 14, 1, 95.00, 8.00),
(9, 16, 1, 899.50, 0.00),
(9, 20, 2, 799.50, 10.00),
(10, 2, 1, 7499.50, 0.00),
(11, 8, 1, 1299.99, 0.00),
(12, 25, 1, 799.50, 0.00);