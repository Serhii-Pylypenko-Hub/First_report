
with base3 as (	
WITH base2 AS (
WITH base AS (
  WITH u AS (
  SELECT 
    user_id,
    DATE_PART('year', MAX(DATE_TRUNC('month', payment_date))) * 12 +
 	DATE_PART('month', MAX(DATE_TRUNC('month', payment_date))) -
 	DATE_PART('year', MIN(DATE_TRUNC('month', payment_date))) * 12 -
 	DATE_PART('month', MIN(DATE_TRUNC('month', payment_date))) AS lifetime_months
--    DATE_PART('month', AGE(MAX(payment_date), MIN(payment_date))) +
--    DATE_PART('year', AGE(MAX(payment_date), MIN(payment_date))) * 12 AS lifetime_months
  FROM project.games_payments
  GROUP BY user_id)
  
  SELECT 
    gp.user_id
    ,gp.game_name as game_name
    ,SUM(revenue_amount_usd) as revenue_amount_usd 
    ,EXTRACT(MONTH FROM payment_date::DATE) AS month_pay
    ,g.language as language_user
    ,g.has_older_device_model as device
    ,g.age as age_user
    ,AVG(lifetime_months) as lifetime_months
  FROM project.games_payments as gp
  LEFT JOIN project.games_paid_users as g
   ON gp.user_id = g.user_id 
  LEFT join u as u
  ON gp.user_id = u.user_id
  group by gp.user_id,gp.game_name, month_pay,g.language,g.has_older_device_model,g.age

)

SELECT 
  user_id
  ,month_pay
  ,revenue_amount_usd
  ,game_name
  ,language_user
  ,device
  ,age_user
  ,LEAD(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) AS next_paid_month
  , month_pay - 1 AS previous_calendar_month
  , month_pay + 1 as next_calendar_month
  ,CASE 
    WHEN LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) IS NULL 
      THEN revenue_amount_usd 
  END AS new_MRR
  ,CASE 
    WHEN LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) IS NULL 
      THEN 1 
  END AS new_paid_users
  ,MAX(month_pay) OVER (PARTITION BY user_id) AS max_month
  ,CASE 
    WHEN LEAD(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) IS NULL
      OR LEAD(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) != (month_pay + 1)
    THEN 1
  END AS last_paid_mons_user

  ,LAG(revenue_amount_usd) OVER (PARTITION BY user_id ORDER BY month_pay) AS prev_mrr
   ,CASE 
    WHEN LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) = month_pay - 1
         AND revenue_amount_usd > LAG(revenue_amount_usd) OVER (PARTITION BY user_id ORDER BY month_pay)
    THEN revenue_amount_usd - LAG(revenue_amount_usd) OVER (PARTITION BY user_id ORDER BY month_pay)
    ELSE 0
  END AS expansion_mrr
      
   ,CASE 
    WHEN LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) = month_pay - 1
         AND revenue_amount_usd < LAG(revenue_amount_usd) OVER (PARTITION BY user_id ORDER BY month_pay)
    THEN revenue_amount_usd - LAG(revenue_amount_usd) OVER (PARTITION BY user_id ORDER BY month_pay)
    ELSE 0
  END AS contraction_mrr  
   ,month_pay - LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) AS months_since_last_payment  
   ,CASE
         	WHEN LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) IS NOT NULL
         	AND LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) < month_pay - 1
    		THEN revenue_amount_usd
  		END AS back_from_churn_mrr 
  ,CASE
    		WHEN LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) IS NOT NULL
    		 AND LAG(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) < month_pay - 1
    		THEN 1
  		END AS back_from_churn_user
   ,CASE
        WHEN LEAD(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) IS NULL
         OR LEAD(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) != (month_pay + 1)
        THEN revenue_amount_usd
      END AS churned_revenue

    ,CASE
        WHEN LEAD(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) IS NULL
         OR LEAD(month_pay) OVER (PARTITION BY user_id ORDER BY month_pay) != (month_pay + 1)
        THEN month_pay + 1
      END AS churn_month
  ,lifetime_months    
   
 FROM base
)
select  
	month_pay
	,round(sum(revenue_amount_usd),0) as MRR
	,count(distinct user_id) as paid_users 
	,round(sum(new_mrr),0) as new_mrr
	,sum(new_paid_users) as new_paid_users
	,sum(last_paid_mons_user) as Churned_Users
	,round(sum(last_paid_mons_user)* 1.0 /count(distinct user_id),2) as Churn_Rate
	,round(sum(churned_revenue),0) AS churned_revenue   	
	,round((sum(CASE 
       	 WHEN last_paid_mons_user = 1 THEN revenue_amount_usd 
        	ELSE 0 
      	END))*1.0/sum(revenue_amount_usd),2) as Revenue_Churn_rate
      	
 	,round(sum(expansion_mrr),0) AS expansion_mrr
 	,round(sum(contraction_mrr),0) as contraction_mrr
 	,sum(back_from_churn_user) AS back_from_churn_users
 	,round(sum(back_from_churn_mrr), 0) AS back_from_churn_mrr
	,count(distinct user_id) as pay_user
	,round(sum(revenue_amount_usd)/count(distinct user_id),0) as ARPPU
	,round(AVG(lifetime_months)::numeric,0) as lifetime_months
	,round(AVG(lifetime_months)::numeric,0) * round(sum(revenue_amount_usd)/count(distinct user_id),0 ) as LTV
from base2
group by  month_pay
order by month_pay
)
select 
	
CASE
    WHEN month_pay = 3 THEN 'March 2022'
    WHEN month_pay = 4 THEN 'April 2022'
    WHEN month_pay = 5 THEN 'May 2022'
    WHEN month_pay = 6 THEN 'June 2022'
    WHEN month_pay = 7 THEN 'July 2022'
    WHEN month_pay = 8 THEN 'August 2022'
    WHEN month_pay = 9 THEN 'September 2022'
    WHEN month_pay = 10 THEN 'October 2022'
    WHEN month_pay = 11 THEN 'November 2022'
    WHEN month_pay = 12 THEN 'December 2022'
      END AS month_pay
	,mrr
	,paid_users
	,new_mrr
	,new_paid_users
	,LAG(churned_users) OVER (ORDER BY month_pay) as churned_users
	,LAG(churn_rate) OVER (ORDER BY month_pay) as churn_rate
	,LAG(churned_revenue) OVER (ORDER BY month_pay) as churn_MMR
	,LAG(Revenue_Churn_rate) OVER (ORDER BY month_pay) as Revenue_Churn_rate
	,expansion_mrr
	,contraction_mrr
	,back_from_churn_users
	,back_from_churn_mrr
	,ARPPU
	,pay_user
	,lifetime_months
--	,ARPPU * lifetime_months as LTV
	,LTV
from base3


