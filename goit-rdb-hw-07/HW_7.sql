#1
SELECT
  id,
  hw_03.orders.date,
  YEAR(hw_03.orders.date)  AS year_part,
  MONTH(hw_03.orders.date) AS month_part,
  DAY(hw_03.orders.date)   AS day_part
FROM orders;
#2
SELECT
    id,
    date,
    DATE_ADD(date, INTERVAL 1 DAY) AS date_plus_1_day
FROM orders;
#3
SELECT
    id,
    date,
    UNIX_TIMESTAMP(date) AS unix_timestamp
FROM orders;
#4
SELECT
    COUNT(*) AS rows_in_range
FROM orders
WHERE date BETWEEN '1996-07-10 00:00:00'
                AND '1996-10-08 00:00:00';
#5
SELECT
    id,
    date,
    JSON_OBJECT(
        'id', id,
        'date', date
    ) AS json_object
FROM orders;





