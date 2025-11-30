#1
SELECT *
FROM hw_03.products;
SELECT 
name, 
phone
FROM hw_03.shippers;

#2

SELECT AVG(price) AS avg_prict,
MAX(price) AS max_prict,
min(price) AS avg_prict
FROM hw_03.products;

#3
SELECT distinct(price)
FROM hw_03.products;

SELECT distinct(category_id)
FROM hw_03.products;

SELECT distinct(price)
FROM hw_03.products
ORDER BY price asc
LIMIT 10;

#4
SELECT *
FROM hw_03.products
WHERE 20 > price < 100;

#5
SELECT count(name),
avg(price)
FROM hw_03.products;
