#3
USE hw_03;

SELECT
    od.id              AS order_detail_id,
    od.quantity,
    o.id               AS order_id,
    c.name             AS customer_name,
    p.name             AS product_name,
    cat.name           AS category_name,
    e.employee_id,
    e.first_name,
    e.last_name,
    sh.name            AS shipper_name,
    sup.name           AS supplier_name
FROM order_details AS od
INNER JOIN orders      AS o   ON od.order_id    = o.id
INNER JOIN customers   AS c   ON o.customer_id  = c.id
INNER JOIN products    AS p   ON od.product_id  = p.id
INNER JOIN categories  AS cat ON p.category_id  = cat.id
INNER JOIN employees   AS e   ON o.employee_id  = e.employee_id
INNER JOIN shippers    AS sh  ON o.shipper_id   = sh.id
INNER JOIN suppliers   AS sup ON p.supplier_id  = sup.id;

#4
#Скільки рядків повертає JOIN (COUNT)
SELECT
    COUNT(*) AS row_count
FROM order_details AS od
INNER JOIN orders      AS o   ON od.order_id    = o.id
INNER JOIN customers   AS c   ON o.customer_id  = c.id
INNER JOIN products    AS p   ON od.product_id  = p.id
INNER JOIN categories  AS cat ON p.category_id  = cat.id
INNER JOIN employees   AS e   ON o.employee_id  = e.employee_id
INNER JOIN shippers    AS sh  ON o.shipper_id   = sh.id
INNER JOIN suppliers   AS sup ON p.supplier_id  = sup.id;
#Замінюємо INNER на LEFT
SELECT
    COUNT(*) AS row_count
FROM order_details AS od
LEFT JOIN orders      AS o   ON od.order_id    = o.id
LEFT JOIN customers   AS c   ON o.customer_id  = c.id
LEFT JOIN products    AS p   ON od.product_id  = p.id
LEFT JOIN categories  AS cat ON p.category_id  = cat.id
LEFT JOIN employees   AS e   ON o.employee_id  = e.employee_id
LEFT JOIN shippers    AS sh  ON o.shipper_id   = sh.id
LEFT JOIN suppliers   AS sup ON p.supplier_id  = sup.id;
#employee_id > 3 AND ≤ 10
SELECT
    od.id            AS order_detail_id,
    od.quantity,
    o.id             AS order_id,
    c.name           AS customer_name,
    p.name           AS product_name,
    cat.name         AS category_name,
    e.employee_id,
    e.first_name,
    e.last_name,
    sh.name          AS shipper_name,
    sup.name         AS supplier_name
FROM order_details AS od
INNER JOIN orders      AS o   ON od.order_id    = o.id
INNER JOIN customers   AS c   ON o.customer_id  = c.id
INNER JOIN products    AS p   ON od.product_id  = p.id
INNER JOIN categories  AS cat ON p.category_id  = cat.id
INNER JOIN employees   AS e   ON o.employee_id  = e.employee_id
INNER JOIN shippers    AS sh  ON o.shipper_id   = sh.id
INNER JOIN suppliers   AS sup ON p.supplier_id  = sup.id
WHERE e.employee_id > 3
  AND e.employee_id <= 10;
#GROUP BY категорією, AVG(quantity), HAVING, ORDER BY, LIMIT
  SELECT
    cat.name          AS category_name,
    COUNT(*)          AS rows_count,
    AVG(od.quantity)  AS avg_quantity
FROM order_details AS od
INNER JOIN orders      AS o   ON od.order_id    = o.id
INNER JOIN customers   AS c   ON o.customer_id  = c.id
INNER JOIN products    AS p   ON od.product_id  = p.id
INNER JOIN categories  AS cat ON p.category_id  = cat.id
INNER JOIN employees   AS e   ON o.employee_id  = e.employee_id
INNER JOIN shippers    AS sh  ON o.shipper_id   = sh.id
INNER JOIN suppliers   AS sup ON p.supplier_id  = sup.id
WHERE e.employee_id > 3
  AND e.employee_id <= 10
GROUP BY cat.name;
#Фільтруємо групи, де середня кількість > 21 (HAVING)
SELECT
    cat.name          AS category_name,
    COUNT(*)          AS rows_count,
    AVG(od.quantity)  AS avg_quantity
FROM order_details AS od
INNER JOIN orders      AS o   ON od.order_id    = o.id
INNER JOIN customers   AS c   ON o.customer_id  = c.id
INNER JOIN products    AS p   ON od.product_id  = p.id
INNER JOIN categories  AS cat ON p.category_id  = cat.id
INNER JOIN employees   AS e   ON o.employee_id  = e.employee_id
INNER JOIN shippers    AS sh  ON o.shipper_id   = sh.id
INNER JOIN suppliers   AS sup ON p.supplier_id  = sup.id
WHERE e.employee_id > 3
  AND e.employee_id <= 10
GROUP BY cat.name
HAVING AVG(od.quantity) > 21;
#Сортуємо за спаданням кількості рядків
SELECT
    cat.name          AS category_name,
    COUNT(*)          AS rows_count,
    AVG(od.quantity)  AS avg_quantity
FROM order_details AS od
INNER JOIN orders      AS o   ON od.order_id    = o.id
INNER JOIN customers   AS c   ON o.customer_id  = c.id
INNER JOIN products    AS p   ON od.product_id  = p.id
INNER JOIN categories  AS cat ON p.category_id  = cat.id
INNER JOIN employees   AS e   ON o.employee_id  = e.employee_id
INNER JOIN shippers    AS sh  ON o.shipper_id   = sh.id
INNER JOIN suppliers   AS sup ON p.supplier_id  = sup.id
WHERE e.employee_id > 3
  AND e.employee_id <= 10
GROUP BY cat.name
HAVING AVG(od.quantity) > 21
ORDER BY rows_count DESC;
#Виводимо 4 рядки, пропустивши перший
SELECT
    cat.name          AS category_name,
    COUNT(*)          AS rows_count,
    AVG(od.quantity)  AS avg_quantity
FROM order_details AS od
INNER JOIN orders      AS o   ON od.order_id    = o.id
INNER JOIN customers   AS c   ON o.customer_id  = c.id
INNER JOIN products    AS p   ON od.product_id  = p.id
INNER JOIN categories  AS cat ON p.category_id  = cat.id
INNER JOIN employees   AS e   ON o.employee_id  = e.employee_id
INNER JOIN shippers    AS sh  ON o.shipper_id   = sh.id
INNER JOIN suppliers   AS sup ON p.supplier_id  = sup.id
WHERE e.employee_id > 3
  AND e.employee_id <= 10
GROUP BY cat.name
HAVING AVG(od.quantity) > 21
ORDER BY rows_count DESC
LIMIT 4 OFFSET 1;   -- пропустити 1 рядок, взяти наступні 4
-- або так само: LIMIT 1, 4
