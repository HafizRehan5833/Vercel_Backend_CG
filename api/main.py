from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
import pandas as pd
import uvicorn

app = FastAPI()

# Allow frontend (React, Vue, etc.) to fetch from API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict to your frontend domain later
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

# API endpoint (NO inputs, fixed for your chart)
@app.get("/processing-days-histogram")
def get_histogram():
    # Fixed bins (30 like your matplotlib code)
    counts, bin_edges = np.histogram(batch_processing["processing_days"], bins=30)

    return JSONResponse(content={
        "raw_processing_days": batch_processing["processing_days"].tolist(),  # all values
        "counts": counts.tolist(),          # histogram counts (y-axis)
        "bin_edges": bin_edges.tolist(),    # histogram bin edges (x-axis)
        "threshold": 2                      # fixed delay threshold
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
        "threshold_days": threshold_days
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
        "threshold": 2  # delay threshold
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
        "threshold": 2  # delay threshold line
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
        "threshold": 2
    })

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)