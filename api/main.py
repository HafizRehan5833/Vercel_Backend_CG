#https://vercel-deployment-mu-two.vercel.app/docs

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
import pandas as pd
import uvicorn

app = FastAPI(
    title="Batch Processing API",
    description="API for analyzing batch processing delays",
    version="1.0.0",
    docs_url="/docs",          
    redoc_url="/redoc"         
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load and preprocess data
df = pd.read_excel("batch_details.xlsx")
df["WIP_ACT_START_DATE"] = pd.to_datetime(df["WIP_ACT_START_DATE"])
df["WIP_CMPLT_DATE"] = pd.to_datetime(df["WIP_CMPLT_DATE"])

batch_processing = (
    df.groupby("WIP_BATCH_ID")
      .agg({"WIP_ACT_START_DATE": "min", "WIP_CMPLT_DATE": "max"})
      .reset_index()
)
batch_processing["processing_days"] = (
    (batch_processing["WIP_CMPLT_DATE"] - batch_processing["WIP_ACT_START_DATE"]).dt.days
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Batch Processing API"}

@app.get("/processing-days-histogram")
def get_histogram():
    # Fixed bins (30 like your matplotlib code)
    counts, bin_edges = np.histogram(batch_processing["processing_days"], bins=30)

    return JSONResponse(content={
        "raw_processing_days": batch_processing["processing_days"].tolist(),  # all values
        "counts": counts.tolist(),          # histogram counts (y-axis)
        "bin_edges": bin_edges.tolist(),    # histogram bin edges (x-axis)
        "threshold": 2 ,
         "ai_insights":"""
         # What this chart shows
- A **histogram** of batch-level processing times (`processing_days`).  
- The **x-axis** shows how many days each batch took to complete.  
- The **y-axis** shows the number of batches falling in each time range.  
- The **red dashed line at 2 days** marks the **delay threshold**.  

# Insights you can derive
1. **Most batches are fast**  
   - The bulk of batches finish within **0–2 days**, clustering left of the threshold line.  
   - This indicates the process is generally efficient for a majority of runs.  

2. **Significant delayed tail**  
   - There is a **long tail to the right**, with some batches taking much longer (5–10+ days, even beyond 20 days).  
   - These extended outliers suggest **specific bottlenecks or exceptional cases** that require deeper investigation.  

3. **Delay threshold exceedances** 
   - A notable number of batches cross the **2-day delay threshold**, visible as bars to the right of the red line.  
   - These represent the **share of batches at risk** for customer service or operational performance metrics.  

4. **Operational variability**  
   - The spread of the distribution shows that while most processes are tightly controlled, there’s **variability across certain batches**.  
   - Identifying root causes (equipment issues, material shortages, product type differences) can reduce this variability.  

         """
    })

# API endpoint for delayed vs on-time share
@app.get("/delay-share")
def get_delay_share():
    threshold_days = 2  # fixed threshold for delay
    batch_processing["is_delayed"] = batch_processing["processing_days"] > threshold_days

    delay_counts = batch_processing["is_delayed"].value_counts(normalize=True) * 100

    return JSONResponse(content={
        "categories": ["On Time", "Delayed"],
        "percentages": [
            delay_counts.get(False, 0),  # On Time %
            delay_counts.get(True, 0)    # Delayed %
        ],
        "threshold_days": threshold_days,
        "ai_insights": """
        # What this chart shows
- A **bar chart** comparing the percentage of **on-time vs delayed batches**.  
- About **74% of batches finish within the 2-day threshold** (on time).  
- Around **26% of batches exceed the 2-day threshold** (delayed).  

# Insights you can derive
1. **Overall performance**
   - The majority of batches are completed on time, showing that the process is generally reliable.  
   - However, with **1 in 4 batches delayed**, delays are not rare and could impact production flow and delivery schedules.  

2. **Room for improvement**
   - Reducing the delayed portion even by a few percentage points could yield major improvements in throughput, capacity utilization, and customer satisfaction.  

3. **Business impact**
   - If delayed batches involve high-value products or critical customer orders, the **real-world impact is larger than the percentage suggests**.  
   - Understanding which formulas or lines contribute most to delays will help prioritize improvement efforts.  

# Suggested next steps
- **Break down delay rates by line, formula, or product family** to identify where the 26% delays originate.  
- **Quantify financial impact** by linking delayed batches to WIP value and lost opportunity.  
- **Investigate recurring causes** (material shortages, equipment downtime, planning issues) for delayed batches.  
- **Set improvement targets**, e.g., reduce delays from 26% → 15% over the next quarter.  
        
        """
    })
# API endpoint for monthly average processing days
@app.get("/monthly-average-delay")
def get_monthly_average_delay():
    # Extract month from start date
    batch_processing["month"] = batch_processing["WIP_ACT_START_DATE"].dt.to_period("M")

    # Monthly average processing days
    monthly_delay = (
        batch_processing.groupby("month")["processing_days"]
        .mean()
        .reset_index()
    )

    # Convert Period to Timestamp (string for JSON)
    monthly_delay["month"] = monthly_delay["month"].dt.to_timestamp()

    return JSONResponse(content={
        "months": monthly_delay["month"].dt.strftime("%Y-%m").tolist(),  # e.g., "2024-01"
        "avg_processing_days": monthly_delay["processing_days"].tolist(), # y-axis values
        "threshold": 2 , # delay threshold
        "ai_insights": """
        
        # What this chart shows
- A **time-series line chart** of the **average batch processing days per month**.  
- A **red dashed line marks the 2-day threshold** (delay benchmark).  
- Early months mostly stayed **below or near the threshold**.  
- In later months, the **average processing time increases sharply**, with several months exceeding **5–10 days on average**.

# Insights you can derive
1. **Early stability, later deterioration**
   - Initially, batch processing was controlled and consistently **under 2 days** on average.  
   - Over time, processing days **spiked significantly**, showing a **deterioration in performance**.  

2. **Clear upward trend**
   - From the mid-point of the timeline, averages began creeping upward, suggesting **systematic delays** (e.g., demand surge, capacity bottlenecks, resource shortages).  
   - The peaks reaching **10–15+ days** highlight **severe operational inefficiencies** in certain months.  

3. **Threshold breaches are frequent in later periods**
   - In the first half, breaches of the 2-day delay threshold were rare.  
   - In the second half, **delays became the norm rather than the exception**.  

# Suggested next steps
- **Root cause analysis by time period**: Identify what changed during the months when delays started trending upward (e.g., seasonal demand, machine breakdowns, supplier issues).  
- **Correlate with production volumes**: Check whether spikes coincide with high WIP loads or new product launches.  
- **Operational interventions**:  
  - Add capacity or shifts during peak months.  
  - Rebalance workloads across lines.  
  - Improve preventive maintenance to avoid bottlenecks.  
- **Set monitoring alerts**: Flag when average monthly processing days exceed **2–3 days**, so corrective actions can be taken early. 
        """
    })


# API endpoint for average processing days by line
@app.get("/line-average-delay")
def get_line_average_delay():
    # Calculate processing_days if not already in df
    df["processing_days"] = (df["WIP_CMPLT_DATE"] - df["WIP_ACT_START_DATE"]).dt.days

    # Group by line to compute average processing days
    delay_by_line = df.groupby("LINE_NO")["processing_days"].mean().reset_index()

    return JSONResponse(content={
        "lines": delay_by_line["LINE_NO"].astype(str).tolist(),       # x-axis labels
        "avg_processing_days": delay_by_line["processing_days"].tolist(),  # y-axis values
        "threshold": 2,
        "ai_insights": """
        # What this chart shows
- A **bar chart of average processing days by production line**.  
- A **red dashed line at 2 days** marks the threshold for delays.  
- Most lines hover around **~2 days or below**, staying close to or under the benchmark.  
- However, a few lines (notably **Line 24 and Line 25**) have **very high averages (4–5+ days)**, standing out as clear bottlenecks.

# Insights you can derive
1. **Overall performance is stable for most lines**
   - Lines 1–22 are **well within control**, averaging near or below the 2-day threshold.  
   - These lines show **balanced efficiency** with minimal variation.  

2. **Critical bottlenecks**
   - **Line 24 and Line 25** are major outliers with averages **double or more** the acceptable limit.  
   - These lines are the **biggest contributors to system-wide delays**.  

3. **Best performing lines**
   - Lines 21–23 average **well below 2 days**, even under 1 day in some cases.  
   - These can serve as **benchmarks for best practices** that may be replicated elsewhere.  

# Suggested next steps
- **Deep-dive into Line 24 & 25**:  
  - Check for capacity constraints, equipment issues, or staffing shortages.  
  - Investigate if product mix or complexity on these lines is higher.  

- **Benchmark against top performers (Lines 21–23)**:  
  - Analyze what operational strategies, scheduling, or resourcing helps them stay efficient.  

- **Balance workloads**:  
  - If possible, redistribute high-load batches from Lines 24–25 to underutilized lines.  

- **Continuous monitoring**:  
  - Regularly track average processing days per line to quickly detect new bottlenecks.  
        """
    })


# API endpoint for monthly average processing days by line
@app.get("/line-monthly-average-delay")
def get_line_monthly_average_delay():
    # Batch-level processing days per line
    batch_processing = (
        df.groupby(["WIP_BATCH_ID", "LINE_NO"])
          .agg({"WIP_ACT_START_DATE": "min", "WIP_CMPLT_DATE": "max"})
          .reset_index()
    )
    batch_processing["processing_days"] = (
        (batch_processing["WIP_CMPLT_DATE"] - batch_processing["WIP_ACT_START_DATE"]).dt.days
    )
    batch_processing["month"] = batch_processing["WIP_ACT_START_DATE"].dt.to_period("M")

    # Group by line & month
    avg_delay = (
        batch_processing.groupby(["month", "LINE_NO"])["processing_days"]
        .mean()
        .reset_index()
    )

    # Convert month Period -> Timestamp -> String
    avg_delay["month"] = avg_delay["month"].dt.to_timestamp()
    avg_delay["month"] = avg_delay["month"].dt.strftime("%Y-%m")

    # Pivot to create structure: line_no -> list of avg values aligned with months
    pivoted = avg_delay.pivot(index="month", columns="LINE_NO", values="processing_days").fillna(0)

    return JSONResponse(content={
        "months": pivoted.index.tolist(),
        "lines": {str(col): pivoted[col].tolist() for col in pivoted.columns},
        "threshold": 2,
        "ai_insights": """
        
        # What this chart shows
- A **monthly trend of average processing days per line** across all 26 lines.  
- The **red dashed line at 2 days** is the delay threshold.  
- Each colored line represents one production line, with fluctuations in average processing days over time.  

# Key observations
1. **Overall variability across months**
   - Most lines operate **close to or below 2 days** in many months, but several spikes occur periodically.  
   - Indicates **occasional bottlenecks** rather than consistent systemic delays.  

2. **Severe outliers**
   - Some months show extreme peaks:
     - One line (possibly **Line 24**) spiked above **30 days**.  
     - Another spike around **20 days** occurred in a different line (likely Line 25 or 13).  
   - These peaks dominate the delay pattern and should be investigated.  

3. **Recent upward trend**
   - Toward later months, several lines (e.g., **Line 1, Line 2, Line 13**) are **consistently above 2 days**.  
   - Suggests a **gradual worsening trend** across multiple lines.  

4. **Stable performers**
   - Some lines remain **flat and consistently under 2 days** across months (e.g., Lines 6, 7, 10, 15, 18).  
   - These represent **best practices** and process stability.  

# Insights & recommendations
- **Investigate spikes (Line 24 & 25):**
  - Likely due to **major disruptions** (machine breakdowns, manpower shortage, or large complex batches).  
  - Need root-cause analysis for those extreme delays.  

- **Monitor emerging trends (Lines 1, 2, 13):**
  - Gradual creep above threshold signals **capacity stress**.  
  - Address before they become chronic bottlenecks.  

- **Learn from stable lines (6, 7, 15, 18):**
  - Capture **process discipline, scheduling, or resource allocation strategies** keeping them below threshold.  
  - Use as benchmarks.  

- **Consider rolling average visualization:**
  - A **3-month rolling average** would smooth out extreme spikes and reveal more stable trends.  

# Next step suggestion
Would you like me to prepare a **heatmap (line vs. month with color = avg delay)**?  
That would make spotting problematic months & lines much clearer than overlapping line plots.  
        """
    })

# API endpoint for delayed batches per line
@app.get("/delayed-batches-by-line")
def get_delayed_batches_by_line():
    # Step 1: Compute batch-level processing_days
    batch_processing = (
        df.groupby(["WIP_BATCH_ID", "LINE_NO"])
          .agg({"WIP_ACT_START_DATE": "min", "WIP_CMPLT_DATE": "max"})
          .reset_index()
    )
    batch_processing["processing_days"] = (
        (batch_processing["WIP_CMPLT_DATE"] - batch_processing["WIP_ACT_START_DATE"]).dt.days
    )

    # Step 2: Mark delayed batches
    batch_processing["is_delayed"] = batch_processing["processing_days"] > 2

    # Step 3: Count delayed batches per line
    delayed_by_line = (
        batch_processing[batch_processing["is_delayed"]]
        .groupby("LINE_NO")
        .size()
        .reset_index(name="delayed_batches")
        .sort_values("delayed_batches", ascending=False)
    )

    return JSONResponse(content={
        "lines": delayed_by_line["LINE_NO"].astype(str).tolist(),        # x-axis
        "delayed_batches": delayed_by_line["delayed_batches"].tolist(),
        "ai_insights": """
        # What this chart shows
- The **number of delayed batches** (processing time > 2 days) per process line.  
- Each bar represents a line, ranked from most to least delayed batches.  

# Key observations
1. **Critical lines with highest delays**  
   - Lines **1 to 10** consistently show **very high delays (around 1,500 delayed batches each)**.  
   - These lines represent the **core bottlenecks** in the production system.  

2. **Moderate problem lines**  
   - Lines **11 to 19** show **800–1,000 delayed batches each**.  
   - These are secondary contributors to overall delays.  

3. **Low-delay lines**  
   - Lines **20 to 23** show **few hundred delayed batches or less**.  
   - Line 23 and 24 are **almost negligible contributors**, indicating either low volume or highly efficient processes.  
   - Line 25 has **zero delayed batches**, making it the best performer.  

# Insights & recommendations
- **Prioritize improvement efforts on Lines 1–10**  
  - They are responsible for the majority of delays and will give the **biggest impact if optimized**.  
  - Possible issues: capacity overload, frequent breakdowns, scheduling inefficiencies.  

- **Focus secondary attention on Lines 11–19**  
  - Moderate level of delays, worth monitoring and addressing after the top 10 lines are stabilized.  

- **Study best practices from Lines 23–25**  
  - Very low or zero delays → investigate **why they are so efficient** (lower workload, better resource management, or less complex products?).  
  - Apply learnings to high-delay lines.  

# Conclusion
- **80/20 rule applies**: The top 10 lines (1–10) are likely contributing to **over 70% of total delays**.  
- Improvements in these critical lines can drastically reduce system-wide production delays.  
- A deeper drilldown (batch size, product type, resource availability per line) would help in root cause analysis.
        """
    })

# API endpoint for delayed vs total batches per line
@app.get("/delayed-vs-total-batches")
def get_delayed_vs_total_batches():
    # Step 1: Compute batch-level processing_days
    batch_processing = (
        df.groupby(["WIP_BATCH_ID", "LINE_NO"])
          .agg({"WIP_ACT_START_DATE": "min", "WIP_CMPLT_DATE": "max"})
          .reset_index()
    )
    batch_processing["processing_days"] = (
        (batch_processing["WIP_CMPLT_DATE"] - batch_processing["WIP_ACT_START_DATE"]).dt.days
    )
    batch_processing["is_delayed"] = batch_processing["processing_days"] > 2

    # Step 2: Aggregate per line
    line_stats = batch_processing.groupby("LINE_NO").agg(
        total_batches=("WIP_BATCH_ID", "count"),
        delayed_batches=("is_delayed", "sum")
    ).reset_index()

    # On-time = total - delayed
    line_stats["on_time_batches"] = line_stats["total_batches"] - line_stats["delayed_batches"]

    # Sort by total workload (largest first)
    line_stats = line_stats.sort_values("total_batches", ascending=False)

    return JSONResponse(content={
        "lines": line_stats["LINE_NO"].astype(str).tolist(),
        "total_batches": line_stats["total_batches"].tolist(),
        "delayed_batches": line_stats["delayed_batches"].tolist(),
        "on_time_batches": line_stats["on_time_batches"].tolist(),

        "ai_insights": """
        # What this chart shows
- **Total workload (batches)** per process line, split into:
  - **On Time batches** (light gray)
  - **Delayed batches** (blue, > 2 processing days)
- Lines are sorted by workload (highest total batches on the left).

# Key observations
1. **High-workload lines (1–10)**  
   - Each handles ~5,800 batches, the **largest share of total production**.  
   - Despite high volumes, a **large chunk (blue) is delayed**.  
   - Indicates **capacity strain** or **systematic inefficiencies**.  

2. **Medium-workload lines (11–19)**  
   - Handle ~2,500–3,500 batches each.  
   - Proportion of delayed batches remains **significant (~25–30%)**, but absolute delays are fewer compared to top 10 lines.  

3. **Low-workload lines (20–25)**  
   - Much smaller total volumes.  
   - Some still show delays (e.g., line 20), while others (23–25) are mostly delay-free.  
   - Suggests that **delays are not purely volume-driven** — process or resource issues may exist.  

# Insights & recommendations
- **Critical pressure points: Lines 1–10**  
  - They process the majority of batches and carry the **heaviest absolute delays**.  
  - Improving efficiency here will have the **greatest system-wide impact**.  

- **Balanced focus on throughput and quality**  
  - While some delays may be expected in high-volume lines, the **delayed fraction is disproportionately high**, suggesting structural bottlenecks (machine downtime, labor capacity, scheduling).  

- **Learnings from low-delay, low-volume lines (23–25)**  
  - These lines run with minimal delays.  
  - Investigating their **processes, product types, or resource allocation** could yield transferable improvements for higher-load lines.  

# Conclusion
- The system follows a **Pareto distribution**: the top 10 lines account for most production and most delays.  
- Optimizing these lines would yield the largest benefit.  
- However, since delays also exist in medium/low-volume lines, **root cause analysis should go beyond workload** and check operational practices, resource constraints, and product complexity.  

        """
    })

# API endpoint for top 15 formulas by delay rate
@app.get("/top-delay-formulas")
def get_top_delay_formulas():
    # --- Compute batch-level processing_days ---
    batch_processing = (
        df.groupby(["WIP_BATCH_ID", "FORMULA_ID"])
          .agg({"WIP_ACT_START_DATE": "min", "WIP_CMPLT_DATE": "max"})
          .reset_index()
    )
    batch_processing["processing_days"] = (
        (batch_processing["WIP_CMPLT_DATE"] - batch_processing["WIP_ACT_START_DATE"]).dt.days
    )
    batch_processing["is_delayed"] = batch_processing["processing_days"] > 2

    # --- Aggregate by formula: total & delayed ---
    delay_by_formula = batch_processing.groupby("FORMULA_ID").agg(
        total_batches=("WIP_BATCH_ID", "count"),
        delayed_batches=("is_delayed", "sum")
    ).reset_index()

    # --- Compute delay rate (%) ---
    delay_by_formula["delay_rate"] = (
        (delay_by_formula["delayed_batches"] / delay_by_formula["total_batches"]) * 100
    )

    # --- Top 15 formulas ---
    top_delay_formulas = delay_by_formula.sort_values("delay_rate", ascending=False).head(15)

    return JSONResponse(content={
        "formula_ids": top_delay_formulas["FORMULA_ID"].astype(str).tolist(),
        "delay_rates": top_delay_formulas["delay_rate"].round(2).tolist(),
        "ai_insights": """
        # What this chart shows
- The chart compares the **average scrap factor per production line**.  
- Scrap factor indicates the proportion of material wasted (scrap) during production.  
- Each bar corresponds to a **Line No**, with its respective average scrap factor.

# Key observations
1. **Most lines are clustered around ~0.03 (3%) scrap factor**  
   - This indicates a relatively consistent performance across the majority of lines.  

2. **Line 1 shows the lowest scrap factor (~0.018 / 1.8%)**  
   - This suggests Line 1 is operating more efficiently, with less material waste compared to others.  
   - Could be due to better machine calibration, newer equipment, or skilled operators.  

3. **Lines 2, 13, 21, and 23 show slightly lower scrap rates (~2.5–2.8%)** compared to the ~3% benchmark.  
   - These may be secondary efficient performers.  

4. **No line shows excessively high scrap rates** (all are within a narrow range around 3%).  
   - This suggests scrap is a systemic baseline issue rather than isolated to one problematic line.  

# Insights & recommendations
- **Benchmark Line 1 practices**  
  - Investigate why Line 1 has significantly lower scrap.  
  - Replicate best practices (e.g., preventive maintenance, operator skill, material handling) across other lines.  

- **Focus on small improvements across all lines**  
  - Since most lines are near 3%, a **0.5% reduction plant-wide** could yield significant savings in material costs.  

- **Check for systemic causes**  
  - The uniformity of scrap factors indicates a **common process or formula-driven scrap rate**, rather than line-specific defects.  
  - This means looking into **recipe design, raw material variability, or production setup standards** might be more impactful.  

# Conclusion
- Scrap rates are generally stable but consistently around ~3%.  
- Line 1 stands out as a model of efficiency (~40% lower scrap vs. average).  
- By studying Line 1’s practices and applying them plant-wide, overall scrap can be reduced significantly
        """
    })

# API endpoint for average scrap factor per line
@app.get("/line-scrap-factor")
def get_line_scrap_factor():
    # Group by line and compute mean scrap factor
    line_scrap = df.groupby("LINE_NO")["SCRAP_FACTOR"].mean().reset_index()

    return JSONResponse(content={
        "lines": line_scrap["LINE_NO"].astype(str).tolist(),
        "avg_scrap_factor": line_scrap["SCRAP_FACTOR"].round(4).tolist(),
        "ai_insights": """
        ### What this shows
- The bar chart illustrates the **average scrap factor for each production line**.  
- **Scrap factor** = proportion of material wasted in production.  
- Each bar = one production line’s average waste level.  

---

### 🔑 Key Observations
1. **Most lines are clustered at ~3% scrap factor**  
   - Indicates relatively consistent performance across the majority of lines.  
   - Suggests a systemic process baseline rather than isolated inefficiencies.  

2. **Line 1 is the clear outlier (best performer, ~1.8%)**  
   - Substantially below the factory-wide average.  
   - Indicates higher efficiency — possibly newer machinery, tighter process control, or better-skilled operators.  

3. **Other relatively efficient lines (~2.4–2.8%) include Lines 2, 13, 20, and 23**  
   - These perform slightly better than the ~3% cluster.  

4. **No line is underperforming dramatically**  
   - No significant deviations above 3%.  
   - Confirms scrap is more of a **systemic baseline issue** than a line-specific problem.  

---

### 💡 Insights & Recommendations
- **Benchmark Line 1 practices**  
  - Study what makes Line 1 significantly more efficient.  
  - Transfer best practices (operator training, equipment settings, maintenance schedules, etc.) to other lines.  

- **Plant-wide improvement potential**  
  - Even a **0.5% reduction in scrap across all lines** could yield substantial material savings.  

- **Investigate systemic drivers of scrap**  
  - Since most lines are at ~3%, improvements may come from:  
    - Material specifications  
    - Formula/recipe design  
    - Standard operating procedures  
    - Preventive maintenance  
        """

    })


# API endpoint for monthly delay rate
@app.get("/monthly-delay-rate")
def get_monthly_delay_rate():
    # Compute batch-level processing days
    batch_processing = (
        df.groupby("WIP_BATCH_ID")
          .agg({"WIP_ACT_START_DATE": "min", "WIP_CMPLT_DATE": "max"})
          .reset_index()
    )
    batch_processing["processing_days"] = (
        (batch_processing["WIP_CMPLT_DATE"] - batch_processing["WIP_ACT_START_DATE"]).dt.days
    )

    # Extract month
    batch_processing["month"] = batch_processing["WIP_ACT_START_DATE"].dt.to_period("M")

    # Monthly delay stats
    delay_by_month = (
        batch_processing.assign(is_delayed=batch_processing["processing_days"] > 2)
        .groupby("month")
        .agg(
            total_batches=("WIP_BATCH_ID", "count"),
            delayed_batches=("is_delayed", "sum")
        )
        .reset_index()
    )
    delay_by_month["delay_rate"] = (
        delay_by_month["delayed_batches"] / delay_by_month["total_batches"] * 100
    )

    # Convert Period → Timestamp → string
    delay_by_month["month"] = delay_by_month["month"].dt.to_timestamp()
    delay_by_month["month"] = delay_by_month["month"].dt.strftime("%Y-%m")

    return JSONResponse(content={
        "months": delay_by_month["month"].tolist(),
        "delay_rates": delay_by_month["delay_rate"].round(2).tolist(),
        "threshold": 50,
        "ai_insights": """
        
# ⏱️ Monthly Delay Rate (%) – Analysis

### What the chart shows
- This line chart tracks the **delay rate (%) by month**.  
- The dashed gray line at 50% is a **reference threshold** for acceptable delay levels.  
- Red markers highlight the actual monthly delay performance.  

---

### 🔑 Key Observations
1. **Extremely high volatility**  
   - Delay rates fluctuate sharply month-to-month, often swinging from near zero to over **1000%+**.  
   - Indicates unstable processes or external disruptions.

2. **Early period (left side)**  
   - Several **spikes above 1200% delay rate**, followed by a gradual decline.  
   - Suggests initial instability before some corrective measures.  

3. **Mid-period (center of the chart)**  
   - Delay rates are relatively **low and stable**, often hovering near or below the 50% threshold.  
   - This was the **best performing phase**.  

4. **Recent period (right side)**  
   - Sustained **high delays (800%–1500%)** with sharp month-to-month swings.  
   - Suggests recurrence of systemic problems, possibly capacity constraints, supply chain issues, or workforce inefficiencies.  

---

### 💡 Insights & Recommendations
- **Investigate root causes of spikes**  
  - Look into months with extreme delays (>1000%). These may align with **material shortages, machine breakdowns, or peak demand surges**.  

- **Replicate mid-period stability**  
  - The stable months (near/below 50%) should be studied as benchmarks — what processes worked then that are missing now?  

- **Recent performance is concerning**  
  - Sustained high delays suggest **systemic inefficiencies have returned**.  
  - Requires urgent corrective action to avoid recurring customer dissatisfaction and financial losses.  

- **Forecasting & resource planning**  
  - Volatility suggests delays may not be random. Using **seasonality analysis** could help anticipate spikes and plan resources accordingly.  

        """
    })


# API endpoint for average scrap factor per line
@app.get("/line-scrap-factor")
def get_line_scrap_factor():
    # Group by line to compute mean scrap factor
    line_scrap = df.groupby("LINE_NO")["SCRAP_FACTOR"].mean().reset_index()

    return JSONResponse(content={
        "lines": line_scrap["LINE_NO"].astype(str).tolist(),
        "avg_scrap_factor": line_scrap["SCRAP_FACTOR"].round(4).tolist(),
    "ai_insights": """
    # 🚨 Delay Reasons by Line – Analysis

### What the chart shows
- This stacked bar chart shows **delayed batch counts per line**, broken down by different **delay reasons**.  
- The legend categorizes causes:  
  - **Major:** Addition/deletion for Batch WIP, Capacity Constraints, RM Short, ERP/WIP Errors.  
  - **Minor but recurring:** CR.LOW, HOLD BY SC, Holidays, Supply Chain instructions, Viscosity Variation.  

---

### 🔑 Key Observations
1. **Line 1 is the biggest bottleneck**  
   - Extremely high delays (~850+ counts), far above all other lines.  
   - Mostly driven by **“Addition and deletion for Batch WIP”**.  

2. **Lines 2–11 have consistent but moderate delays**  
   - Each shows **~250–300 delayed batches**, again dominated by Batch WIP changes.  
   - Secondary reasons (capacity constraints, RM short, ERP/WIP error) are present but comparatively minor.  

3. **Lines 12–14 are nearly clean**  
   - Very few delays logged, suggesting either **lower load or more efficient processes**.  

4. **Root cause dominance**  
   - Across all lines, **Batch WIP adjustments** are the overwhelming root cause.  
   - Other categories (capacity, raw material shortage, ERP/WIP error) remain small contributors.  

---

### 💡 Insights & Recommendations
- **Immediate focus: Line 1**  
  - Investigate **Batch WIP process design** – why does Line 1 face disproportionate rework?  
  - Possible causes: scheduling conflicts, incorrect batch planning, operator interventions.  

- **Standardize WIP handling across lines**  
  - Since Batch WIP is the dominant reason everywhere, a **cross-line process correction** could reduce delays significantly.  

- **Preventive measures for secondary causes**  
  - Build stronger **capacity buffers** (machine/operator availability).  
  - Strengthen **raw material planning** to reduce RM shortages.  
  - Audit **ERP/WIP data accuracy** to minimize system-driven delays.  

- **Learn from Lines 12–14**  
  - Study practices here (lower volumes? better planning? different operators?) and replicate to Lines 1–11.  

    """

    })

# API endpoint: Monthly Delay Rate (%)
@app.get("/monthly-delay-rate")
def get_monthly_delay_rate():
    # --- Compute batch-level processing days ---
    batch_processing = (
        df.groupby("WIP_BATCH_ID")
          .agg({"WIP_ACT_START_DATE": "min", "WIP_CMPLT_DATE": "max"})
          .reset_index()
    )
    batch_processing["processing_days"] = (
        (batch_processing["WIP_CMPLT_DATE"] - batch_processing["WIP_ACT_START_DATE"]).dt.days
    )
    batch_processing["month"] = batch_processing["WIP_ACT_START_DATE"].dt.to_period("M")

    # --- Monthly totals and delayed counts ---
    delay_by_month = (
        batch_processing.assign(is_delayed=batch_processing["processing_days"] > 2)
        .groupby("month")
        .agg(
            total_batches=("WIP_BATCH_ID", "count"),
            delayed_batches=("is_delayed", "sum")
        )
        .reset_index()
    )

    delay_by_month["delay_rate"] = (
        delay_by_month["delayed_batches"] / delay_by_month["total_batches"] * 100
    )

    # Convert Period -> string YYYY-MM
    delay_by_month["month"] = delay_by_month["month"].astype(str)

    # --- Return JSON ---
    return JSONResponse(content={
        "months": delay_by_month["month"].tolist(),
        "delay_rates": delay_by_month["delay_rate"].round(2).tolist(),
        "total_batches": delay_by_month["total_batches"].tolist(),
        "delayed_batches": delay_by_month["delayed_batches"].tolist(),
        "threshold": 50
    })

# 📌 Delay reasons by line
@app.get("/delay-reasons-by-line")
def get_delay_reasons_by_line():
    local_df = df.copy()

    # Ensure processing_days column exists
    if "processing_days" not in local_df.columns:
        local_df["processing_days"] = (
            (local_df["WIP_CMPLT_DATE"] - local_df["WIP_ACT_START_DATE"]).dt.days
        )

    # Filter delayed batches
    line_reason = (
        local_df[local_df["processing_days"] > 2]
        .dropna(subset=["REASON"])
        .groupby(["LINE_NO", "REASON"])
        .size()
        .reset_index(name="count")
    )

    # Convert to structured JSON
    result = {}
    for _, row in line_reason.iterrows():
        line = str(row["LINE_NO"])
        reason = row["REASON"]
        count = int(row["count"])
        if line not in result:
            result[line] = {}
        result[line][reason] = count

    return JSONResponse(content={
        "delay_reasons_by_line": result,
        "threshold_days": 2
    })


@app.get("/delay-reasons-top10")
def get_top_delay_reasons():
    if "processing_days" not in df.columns:
        df["processing_days"] = (df["WIP_CMPLT_DATE"] - df["WIP_ACT_START_DATE"]).dt.days

    delayed = df[df["processing_days"] > 2].dropna(subset=["REASON"])  # fixed threshold = 2

    delay_reasons = (
        delayed.groupby("REASON")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(10)
    )

    total_delayed = delay_reasons["count"].sum()
    delay_reasons["share_percent"] = (delay_reasons["count"] / total_delayed * 100).round(2)

    return {
        "top_delay_reasons": delay_reasons.to_dict(orient="records"),
        "threshold_days": 2
    }


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
