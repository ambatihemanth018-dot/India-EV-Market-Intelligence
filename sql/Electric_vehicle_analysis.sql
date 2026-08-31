
CREATE DATABASE Electric_vehicle;
GO

USE Electric_vehicle;
GO

CREATE TABLE dim_date
    ([date] DATE PRIMARY KEY,
    fiscal_year INT,
    quarter VARCHAR(5)
);

CREATE TABLE Electric_vehicle_sales_by_state
    ([date] DATE,
    state VARCHAR(100),
    vehicle_category VARCHAR(20),
    electric_vehicles_sold INT,
    total_vehicles_sold INT,

    FOREIGN KEY([date])
    REFERENCES dim_date([date])
);

CREATE TABLE Electric_vehicle_sales_by_makers
    ([date] DATE,
    vehicle_category VARCHAR(20),
    maker VARCHAR(100),
    electric_vehicles_sold INT,

    FOREIGN KEY([date])
    REFERENCES dim_date([date])
);

BULK INSERT dim_date
FROM dim_date = pd.read_csv("../data/dim_date.csv")
WITH
(
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK
);

BULK INSERT Electric_vehicle_sales_by_state
FROM state_sales = pd.read_csv("../data/electric_vehicle_sales_by_state.csv")
WITH
(
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK
);

BULK INSERT Electric_vehicle_sales_by_makers
FROM maker_sales = pd.read_csv("../data/electric_vehicle_sales_by_makers.csv")
WITH
(
    FIRSTROW = 2,
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    TABLOCK
);



-- Top 3 and Bottom 3 makers for the fiscal years 2023 and 2024 in terms of the number of 2-wheelers sold --

WITH maker_sales AS

   (SELECT d.fiscal_year,m.maker,SUM(m.electric_vehicles_sold) AS total_sales,
    DENSE_RANK() OVER (PARTITION BY d.fiscal_year ORDER BY SUM (m.electric_vehicles_sold) DESC) AS top_rank,
    DENSE_RANK() OVER (PARTITION BY d.fiscal_year ORDER BY SUM(m.electric_vehicles_sold)) AS bottom_rank
    FROM electric_vehicle_sales_by_makers m
    JOIN dim_date d ON m.date=d.date
    WHERE vehicle_category='2-Wheelers' AND fiscal_year IN (2023,2024)
    GROUP BY d.fiscal_year,maker)

SELECT * FROM maker_sales
WHERE top_rank<=3 OR bottom_rank<=3
ORDER BY fiscal_year,total_sales DESC;



-- Top 5 States by Penetration Rate --

SELECT TOP 5 state,vehicle_category,SUM(electric_vehicles_sold)*100.0/SUM(total_vehicles_sold) AS penetration_rate
FROM electric_vehicle_sales_by_state s
JOIN dim_date d ON s.date=d.date
WHERE fiscal_year = 2024
GROUP BY state,vehicle_category
ORDER BY penetration_rate DESC;



-- Quarterly Trends (Top 5 Makers - 4 Wheelers)

WITH top5 AS
(SELECT TOP 5 maker,SUM(electric_vehicles_sold) AS sales
FROM electric_vehicle_sales_by_makers m
JOIN dim_date d ON m.date=d.date
WHERE vehicle_category='4-Wheelers'
GROUP BY maker
ORDER BY sales DESC)

SELECT maker,fiscal_year,quarter,SUM(electric_vehicles_sold) AS quarterly_sales
FROM electric_vehicle_sales_by_makers m
JOIN dim_date d ON m.date=d.date
WHERE maker IN

(SELECT maker FROM top5)
GROUP BY maker,fiscal_year,quarter
ORDER BY maker,fiscal_year,quarter;



-- CAGR (Top 5 Makers - 4 Wheelers) --

WITH maker_sales AS

  ( SELECT m.maker,d.fiscal_year,SUM(m.electric_vehicles_sold) AS sales
    FROM electric_vehicle_sales_by_makers m
    JOIN dim_date d ON m.date = d.date
    WHERE m.vehicle_category = '4-Wheelers'AND d.fiscal_year IN (2022, 2024)
    GROUP BY m.maker,d.fiscal_year ),

pivot_sales AS

  ( SELECT maker,
           MAX(CASE WHEN fiscal_year = 2022 THEN sales END) AS sales_2022,
           MAX(CASE WHEN fiscal_year = 2024 THEN sales END) AS sales_2024
    FROM maker_sales
    GROUP BY maker )

SELECT TOP 5 maker,sales_2022,sales_2024,
             ROUND((POWER(sales_2024 * 1.0 /NULLIF(sales_2022,0),1.0/2) - 1) * 100,2) AS CAGR
FROM pivot_sales
WHERE sales_2022 > 0 AND sales_2024 IS NOT NULL
ORDER BY CAGR DESC;




-- Top 10 States CAGR (Total Vehicles) --

WITH sales AS

            (SELECT state,fiscal_year,SUM(total_vehicles_sold) total_sales
             FROM electric_vehicle_sales_by_state s
             JOIN dim_date d ON s.date=d.date
             GROUP BY state,fiscal_year),

pivot_sales AS

           (SELECT state,
                   MAX(CASE WHEN fiscal_year=2022 THEN total_sales END) sales2022,
                   MAX(CASE WHEN fiscal_year=2024 THEN total_sales END) sales2024
                   FROM sales
                   GROUP BY state)

           SELECT TOP 10 state,(POWER((sales2024*1.0/sales2022),0.5)-1)*100 AS CAGR
           FROM pivot_sales
           ORDER BY CAGR DESC;



-- How EV penetration changed over the last three years --

SELECT
    d.fiscal_year,
    SUM(s.electric_vehicles_sold) AS total_ev_sales,
    SUM(s.total_vehicles_sold) AS total_vehicle_sales,
    ROUND( SUM(s.electric_vehicles_sold) * 100.0 /SUM(s.total_vehicles_sold),2
    ) AS penetration_rate
FROM electric_vehicle_sales_by_state s
JOIN dim_date d
ON s.date = d.date
GROUP BY d.fiscal_year
ORDER BY d.fiscal_year;



-- Which states have high total vehicle sales but low EV penetration -- 

SELECT state,
       SUM(total_vehicles_sold) AS total_vehicle_sales,
       SUM(electric_vehicles_sold) AS ev_sales,
       ROUND(SUM(electric_vehicles_sold)*100.0/SUM(total_vehicles_sold),2)
       AS penetration_rate
       FROM electric_vehicle_sales_by_state
       GROUP BY state
       ORDER BY
       penetration_rate ASC,
       total_vehicle_sales DESC;



-- Are 2-Wheelers growing faster than 4-Wheelers --

SELECT d.fiscal_year,vehicle_category,SUM(electric_vehicles_sold) AS total_sales
FROM electric_vehicle_sales_by_state s
JOIN dim_date d ON s.date=d.date
GROUP BY d.fiscal_year,vehicle_category
ORDER BY vehicle_category,d.fiscal_year;



-- Which states prefer 2W and 4W --

SELECT state,vehicle_category,SUM(electric_vehicles_sold) AS total_sales
FROM electric_vehicle_sales_by_state
GROUP BY state,vehicle_category
ORDER BY state,total_sales DESC;



-- Which months have peak EV demand -- 

SELECT TOP 5
       DATENAME(MONTH,date) AS month_name,
       MONTH(date) AS month_no,
       SUM(electric_vehicles_sold) AS total_sales
FROM Electric_vehicle_sales_by_state
GROUP BY MONTH(date),DATENAME(MONTH,date)
ORDER BY total_sales DESC;



-- Which months have the lowest EV demand --

SELECT TOP 5
       DATENAME(MONTH,date) AS month_name,
       MONTH(date) AS month_no,
       SUM(electric_vehicles_sold) AS total_sales
FROM electric_vehicle_sales_by_state
GROUP BY MONTH(date),DATENAME(MONTH,date)
ORDER BY total_sales ASC;

