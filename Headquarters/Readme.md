# 🌍 Office Location Environment Analysis – Google vs Microsoft

This project evaluates and compares the surrounding urban environment of Google and Microsoft offices worldwide.  
Using **Power BI** and **Python (embedded in Power Query)**, it retrieves nearby Points of Interest (POIs) from OpenStreetMap, calculates weighted scores based on distance, and presents an interactive dashboard.

![Dashboard Overview](images/dashboard_overview.png)

## 📌 Overview

The goal is to quantify how well-located each office is in terms of access to:
- **Public transport** (stations, bus stops, airports)
- **Education** (schools, universities, libraries)
- **Health** (hospitals, clinics, pharmacies)
- **Leisure** (parks, sports centres, attractions)
- **Restaurants & cafes**
- **Commerce** (supermarkets, banks, shops)

A higher score means more and closer amenities within a 3 km radius.

## 🚀 Features

- **Python-powered data extraction** – Connects to the Overpass API (OpenStreetMap) directly from Power Query.
- **Distance weighting** – Uses the Haversine formula (corrected) so that closer POIs contribute more points.
- **Scaled base scores** – Important places (e.g., hospital = 50 pts, university = 35 pts) get higher weight.
- **No artificial cap** – Scores are cumulative; values can be >100, making differences visible.
- **Interactive Power BI dashboard** – Includes:
  - Bubble map of offices (size = total score)
  - Detailed table of top 10 nearby places per office
  - Breakdown by category (Transport, Health, etc.)
  - Slicers for company, city, and score range

## 🛠️ Technologies

| Tool | Purpose |
|------|---------|
| **Power BI Desktop** | Dashboard & visualisation |
| **Python 3.9+** | Data extraction & processing |
| **Overpass API** | Free OpenStreetMap data |
| **Pandas / Requests** | Python libraries used |
| **GitHub** | Portfolio hosting |

## 📂 Repository Structure
