#1
CREATE SCHEMA IF NOT EXISTS pandemic;
USE pandemic;
SHOW TABLES;
SELECT * FROM infectious_cases;
#2
describe infectious_cases;

SELECT COUNT(*) AS rows_loaded FROM infectious_cases;
USE pandemic;

CREATE TABLE locations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    UNIQUE KEY uq_entity_code (entity, code)
);
CREATE TABLE infectious_cases_norm (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    location_id INT NOT NULL,
    year INT NOT NULL,
    disease VARCHAR(50) NOT NULL,
    cases DECIMAL(15,6),

    CONSTRAINT fk_location
        FOREIGN KEY (location_id)
        REFERENCES locations(id)
);
SHOW TABLES;
USE pandemic;

INSERT INTO locations (entity, code)
SELECT DISTINCT Entity, Code
FROM infectious_cases
WHERE Entity IS NOT NULL;
SELECT COUNT(*) AS locations_cnt
FROM locations;

INSERT INTO infectious_cases_norm (location_id, year, disease, cases)

-- rabies
SELECT
    l.id,
    ic.Year,
    'rabies' AS disease,
    CAST(NULLIF(ic.Number_rabies,'') AS DECIMAL(15,6)) AS cases
FROM infectious_cases ic
JOIN locations l
  ON l.entity = ic.Entity AND (l.code <=> ic.Code)
WHERE ic.Number_rabies <> ''

UNION ALL

-- yaws
SELECT
    l.id,
    ic.Year,
    'yaws' AS disease,
    CAST(NULLIF(ic.Number_yaws,'') AS DECIMAL(15,6)) AS cases
FROM infectious_cases ic
JOIN locations l
  ON l.entity = ic.Entity AND (l.code <=> ic.Code)
WHERE ic.Number_yaws <> ''

UNION ALL

-- polio
SELECT
    l.id,
    ic.Year,
    'polio' AS disease,
    CAST(NULLIF(ic.polio_cases,'') AS DECIMAL(15,6)) AS cases
FROM infectious_cases ic
JOIN locations l
  ON l.entity = ic.Entity AND (l.code <=> ic.Code)
WHERE ic.polio_cases <> ''

UNION ALL

-- malaria
SELECT
    l.id,
    ic.Year,
    'malaria' AS disease,
    CAST(NULLIF(ic.Number_malaria,'') AS DECIMAL(15,6)) AS cases
FROM infectious_cases ic
JOIN locations l
  ON l.entity = ic.Entity AND (l.code <=> ic.Code)
WHERE ic.Number_malaria <> '';

SELECT COUNT(*) AS norm_cnt
FROM infectious_cases_norm;

#3

SELECT
    Entity,
    Code,
    AVG(CAST(Number_rabies AS DECIMAL(15,6))) AS avg_rabies,
    MIN(CAST(Number_rabies AS DECIMAL(15,6))) AS min_rabies,
    MAX(CAST(Number_rabies AS DECIMAL(15,6))) AS max_rabies,
    SUM(CAST(Number_rabies AS DECIMAL(15,6))) AS sum_rabies
FROM infectious_cases
WHERE Number_rabies IS NOT NULL
  AND Number_rabies <> ''
GROUP BY Entity, Code
ORDER BY avg_rabies DESC
LIMIT 10;


#4

SELECT 
    'Year' AS year_value,
    MAKEDATE('Year' , 1) AS year_start_date,
    CURDATE() AS current_date,
    TIMESTAMPDIFF(YEAR, MAKEDATE('Year' , 1), CURDATE()) AS years_diff
FROM infectious_cases
WHERE 'Year'  IS NOT NULL
LIMIT 10;
SELECT *  FROM infectious_cases;

#5

DELIMITER //

DROP FUNCTION IF EXISTS years_from_year //

CREATE FUNCTION years_from_year(input_year INT)
RETURNS INT
DETERMINISTIC
BEGIN
    RETURN TIMESTAMPDIFF(
        YEAR,
        MAKEDATE(input_year, 1),
        CURDATE()
    );
END //
DELIMITER ;
SELECT
    Year,
    years_from_year(Year) AS years_diff
FROM infectious_cases
WHERE Year IS NOT NULL
LIMIT 10;























































