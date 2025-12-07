SELECT * FROM hw_03.order_details od;
#1
 SELECT     od.*,
    (   SELECT o.customer_id
        FROM hw_03.orders AS o
        WHERE o.id = od.order_id) AS customer_id
FROM hw_03.order_details AS od;
#2
SELECT *
FROM hw_03.order_details od
WHERE od.order_id IN (
    SELECT o.id
    FROM hw_03.orders o
    WHERE o.shipper_id = 3
);
#3
SELECT 
    p.*,
    c.name AS category_name      
FROM hw_03.products p
LEFT JOIN hw_03.categories c 
    ON c.id = p.category_id
WHERE p.price > (
    SELECT AVG(p2.price)
    FROM hw_03.products p2
    WHERE p2.category_id = p.category_id
);
#4
WITH temp AS (
    SELECT *
    FROM hw_03.order_details
    WHERE quantity > 10
)
SELECT 
    temp.order_id,
    AVG(temp.quantity) AS avg_quantity
FROM temp
GROUP BY temp.order_id;
#5
DELIMITER //

CREATE FUNCTION divide_numbers(
    num1 FLOAT,
    num2 FLOAT
)
RETURNS FLOAT
DETERMINISTIC
NO SQL
BEGIN
    -- Захист від ділення на нуль
    IF num2 = 0 THEN
        RETURN NULL;
    END IF;

    RETURN num1 / num2;
END //

DELIMITER ;
#Наприклад, ділимо кількість на 2:
SELECT 
    od.order_id,
    od.quantity,
    divide_numbers(od.quantity, 2) AS divided_quantity
FROM hw_03.order_details od;
#наприклад, 3.5:
SELECT 
    od.order_id,
    od.quantity,
    divide_numbers(od.quantity, 3.5) AS divided_quantity
FROM hw_03.order_details od;



