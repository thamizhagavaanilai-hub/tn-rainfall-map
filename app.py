# ================================================================
# TAMIL NADU ACCUMULATED RAINFALL
# PROFESSIONAL A4 PORTRAIT MAP
# ================================================================
#
# 0–5 mm       = WHITE
# 5–10 mm      = VERY LIGHT GREEN
# 10–25 mm     = GREEN
# 25–50 mm     = CYAN
# 50–75 mm     = BLUE-CYAN
# 75–100 mm    = BLUE
# 100–125 mm   = DEEP BLUE
# 125–150 mm   = YELLOW
# 150–175 mm   = GOLD
# 175–200 mm   = ORANGE
# 200–225 mm   = DARK ORANGE
# 225–250 mm   = RED
# 250–275 mm   = DARK RED
# 275–300 mm   = MAROON
#
# ================================================================


# ================================================================
# 1. IMPORT LIBRARIES
# ================================================================

import os
import warnings
import requests

import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt

from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter

from matplotlib.colors import (
    ListedColormap,
    BoundaryNorm
)

from matplotlib.patches import (
    Rectangle,
    FancyBboxPatch
)

from matplotlib.ticker import FuncFormatter

from shapely import contains_xy

import matplotlib.patheffects as pe

from PIL import Image


warnings.filterwarnings("ignore")


# ================================================================
# 2. USER SETTINGS
# ================================================================

start_date = "2026-09-01"

end_date = "2026-09-23"


# ================================================================
# 3. TAMIL NADU DISTRICT SHAPEFILE
# ================================================================

shapefile_path = (
    r"D:\Arun\weather\tn Dsitrict.shp"
)


# ================================================================
# 4. OUTPUT FOLDER
# ================================================================

output_folder = (
    r"D:\Arun\weather"
)

os.makedirs(
    output_folder,
    exist_ok=True
)


# ================================================================
# 5. OUTPUT FILES
# ================================================================

output_png = os.path.join(
    output_folder,
    "TN_Accumulated_Rainfall_A4_Professional.png"
)

output_csv = os.path.join(
    output_folder,
    "TN_Accumulated_Rainfall.csv"
)


# ================================================================
# 6. TN-SMART URL
# ================================================================

rainfall_url = (
    "https://beta-tnsmart.rimes.int/"
    "index.php/MIS/Rainfall/raingauge_stations"
)


# ================================================================
# 7. IDW SETTINGS
# ================================================================

GRID_NX = 700
GRID_NY = 700

IDW_POWER = 2.0

IDW_K = 20

SMOOTH_SIGMA = 2.0


# ================================================================
# 8. RAINFALL RANGE
# ================================================================

RAIN_MIN = 0

RAIN_MAX = 300


# ================================================================
# 9. RAINFALL CLASS BREAKS
# ================================================================
#
# EXACT CLASSES:
#
# 0–5
# 5–10
# 10–25
# 25–50
# 50–75
# 75–100
# 100–125
# 125–150
# 150–175
# 175–200
# 200–225
# 225–250
# 250–275
# 275–300
#
# ================================================================

rain_breaks = [

    0,
    5,
    10,
    25,
    50,
    75,
    100,
    125,
    150,
    175,
    200,
    225,
    250,
    275,
    300

]


# ================================================================
# 10. PROFESSIONAL RAINFALL COLOURS
# ================================================================

rain_colors = [

    # 0–5 mm
    "#FFFFFF",

    # 5–10 mm
    "#E8F5E9",

    # 10–25 mm
    "#00A651",

    # 25–50 mm
    "#00C8C8",

    # 50–75 mm
    "#0099CC",

    # 75–100 mm
    "#0066CC",

    # 100–125 mm
    "#0033CC",

    # 125–150 mm
    "#FFFF00",

    # 150–175 mm
    "#FFD000",

    # 175–200 mm
    "#FFA000",

    # 200–225 mm
    "#FF6600",

    # 225–250 mm
    "#FF0000",

    # 250–275 mm
    "#CC0000",

    # 275–300 mm
    "#800000"

]


# ================================================================
# 11. CREATE DISCRETE COLOUR MAP
# ================================================================

rain_cmap = ListedColormap(
    rain_colors,
    name="TN_RAINFALL"
)


# ================================================================
# 12. CREATE EXACT CLASS NORMALIZATION
# ================================================================

rain_norm = BoundaryNorm(

    rain_breaks,

    rain_cmap.N,

    clip=True

)


# ================================================================
# 13. HTTP HEADERS
# ================================================================

headers = {

    "User-Agent":
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36",

    "Accept":
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8",

    "Accept-Language":
        "en-US,en;q=0.9",

    "Connection":
        "keep-alive"

}


# ================================================================
# 14. FIND COLUMN BY KEYWORD
# ================================================================

def find_column_by_keyword(
    df,
    keywords
):

    for column in df.columns:

        column_text = (
            str(column)
            .strip()
            .lower()
        )

        for keyword in keywords:

            if keyword.lower() in column_text:

                return column

    return None


# ================================================================
# 15. CLEAN DATAFRAME COLUMNS
# ================================================================

def clean_dataframe_columns(df):

    if isinstance(
        df.columns,
        pd.MultiIndex
    ):

        df.columns = [

            " ".join(

                [
                    str(x)

                    for x in col

                    if str(x).lower()
                    != "nan"

                ]

            ).strip()

            for col in df.columns

        ]

    else:

        df.columns = [

            str(col).strip()

            for col in df.columns

        ]

    return df


# ================================================================
# 16. DOWNLOAD DAILY RAINFALL
# ================================================================

def download_daily_rainfall(
    date_string
):

    print()
    print("=" * 70)

    print(
        f"Downloading rainfall: {date_string}"
    )

    print("=" * 70)


    post_data = {

        "date_on": date_string,

        "search_submit": "View Data"

    }


    try:

        response = requests.post(

            rainfall_url,

            data=post_data,

            headers=headers,

            timeout=60

        )

        response.raise_for_status()

    except Exception as e:

        print(
            "ERROR downloading data:"
        )

        print(e)

        return None


    # ============================================================
    # READ HTML TABLES
    # ============================================================

    try:

        tables = pd.read_html(
            response.text
        )

    except Exception as e:

        print(
            "ERROR reading HTML tables:"
        )

        print(e)

        return None


    print(
        f"HTML tables found: {len(tables)}"
    )


    # ============================================================
    # FIND RAINFALL TABLE
    # ============================================================

    rainfall_table = None


    for i, table in enumerate(
        tables
    ):

        table = clean_dataframe_columns(
            table
        )


        lat_col = find_column_by_keyword(

            table,

            [
                "latitude"
            ]

        )


        lon_col = find_column_by_keyword(

            table,

            [
                "longitude"
            ]

        )


        rain_col = find_column_by_keyword(

            table,

            [
                "rainfall recorded",
                "rainfall"
            ]

        )


        if (

            lat_col is not None

            and

            lon_col is not None

            and

            rain_col is not None

        ):

            rainfall_table = table

            print(
                f"Rainfall table found: Table {i}"
            )

            break


    if rainfall_table is None:

        print(
            "ERROR: Rainfall table not found."
        )

        return None


    df = rainfall_table.copy()


    # ============================================================
    # FIND COLUMNS
    # ============================================================

    station_col = find_column_by_keyword(

        df,

        [
            "name of the station",
            "station name",
            "station"
        ]

    )


    location_col = find_column_by_keyword(

        df,

        [
            "district/taluk/revenue village",
            "district/taluk",
            "village"
        ]

    )


    lat_col = find_column_by_keyword(

        df,

        [
            "latitude"
        ]

    )


    lon_col = find_column_by_keyword(

        df,

        [
            "longitude"
        ]

    )


    rain_col = find_column_by_keyword(

        df,

        [
            "rainfall recorded",
            "rainfall"
        ]

    )


    print()
    print(
        "Detected columns"
    )

    print("-" * 60)

    print(
        "Station   :",
        station_col
    )

    print(
        "Location  :",
        location_col
    )

    print(
        "Latitude  :",
        lat_col
    )

    print(
        "Longitude :",
        lon_col
    )

    print(
        "Rainfall  :",
        rain_col
    )

    print("-" * 60)


    if (

        lat_col is None

        or

        lon_col is None

        or

        rain_col is None

    ):

        print(
            "ERROR: Required columns missing."
        )

        return None


    # ============================================================
    # CREATE CLEAN DATAFRAME
    # ============================================================

    result = pd.DataFrame()


    if station_col is not None:

        result["station"] = (

            df[station_col]

            .astype(str)

            .str.strip()

        )

    else:

        result["station"] = "Unknown"


    if location_col is not None:

        result["location"] = (

            df[location_col]

            .astype(str)

            .str.strip()

        )

    else:

        result["location"] = ""


    result["latitude"] = pd.to_numeric(

        df[lat_col]

        .astype(str)

        .str.replace(
            ",",
            "",
            regex=False
        )

        .str.strip(),

        errors="coerce"

    )


    result["longitude"] = pd.to_numeric(

        df[lon_col]

        .astype(str)

        .str.replace(
            ",",
            "",
            regex=False
        )

        .str.strip(),

        errors="coerce"

    )


    # ============================================================
    # CLEAN RAINFALL
    # ============================================================

    rainfall_clean = (

        df[rain_col]

        .astype(str)

        .str.replace(
            ",",
            "",
            regex=False
        )

        .str.replace(
            "mm",
            "",
            case=False,
            regex=False
        )

        .str.strip()

    )


    rainfall_clean = rainfall_clean.replace(

        [
            "-",
            "--",
            "",
            "nan",
            "NaN",
            "None"
        ],

        "0"

    )


    result["daily_rain"] = pd.to_numeric(

        rainfall_clean,

        errors="coerce"

    )


    # ============================================================
    # REMOVE INVALID VALUES
    # ============================================================

    result = result.dropna(

        subset=[

            "latitude",
            "longitude",
            "daily_rain"

        ]

    )


    # ============================================================
    # TAMIL NADU EXTENT FILTER
    # ============================================================

    result = result[

        (result["latitude"] >= 7.0)

        &

        (result["latitude"] <= 14.5)

        &

        (result["longitude"] >= 76.0)

        &

        (result["longitude"] <= 80.8)

    ]


    result = result[

        result["daily_rain"] >= 0

    ]


    result["date"] = date_string


    print(
        f"Valid stations: {len(result)}"
    )


    return result


# ================================================================
# 17. CREATE DATE RANGE
# ================================================================

date_range = pd.date_range(

    start=start_date,

    end=end_date,

    freq="D"

)


# ================================================================
# 18. DOWNLOAD ALL DAYS
# ================================================================

all_daily_data = []


print()
print("#" * 70)

print(
    "TN-SMART RAINFALL DOWNLOAD"
)

print("#" * 70)

print(
    f"Start : {start_date}"
)

print(
    f"End   : {end_date}"
)

print(
    f"Days  : {len(date_range)}"
)

print("#" * 70)


for current_date in date_range:

    date_string = current_date.strftime(
        "%Y-%m-%d"
    )


    daily_data = download_daily_rainfall(

        date_string

    )


    if daily_data is not None:

        if len(daily_data) > 0:

            all_daily_data.append(
                daily_data
            )


# ================================================================
# 19. CHECK DATA
# ================================================================

if len(all_daily_data) == 0:

    raise RuntimeError(
        "No rainfall data was downloaded."
    )


# ================================================================
# 20. COMBINE DAILY DATA
# ================================================================

daily_rainfall = pd.concat(

    all_daily_data,

    ignore_index=True

)


print()
print(
    "Total daily records:",
    len(daily_rainfall)
)


# ================================================================
# 21. STATION-WISE ACCUMULATION
# ================================================================

station_rain = (

    daily_rainfall

    .groupby(

        [
            "station",
            "location",
            "latitude",
            "longitude"
        ],

        as_index=False

    )[

        "daily_rain"

    ]

    .sum()

)


station_rain = station_rain.rename(

    columns={

        "daily_rain":
            "total_rain"

    }

)


# ================================================================
# 22. CLEAN STATION DATA
# ================================================================

station_rain = station_rain.dropna(

    subset=[

        "latitude",
        "longitude",
        "total_rain"

    ]

)


station_rain = station_rain[

    station_rain["total_rain"] >= 0

]


# ================================================================
# 23. REMOVE DUPLICATE STATIONS
# ================================================================

station_rain = (

    station_rain

    .sort_values(

        "total_rain",

        ascending=False

    )

    .drop_duplicates(

        subset=[

            "station",
            "latitude",
            "longitude"

        ],

        keep="first"

    )

    .reset_index(drop=True)

)


# ================================================================
# 24. SAVE CSV
# ================================================================

station_rain.to_csv(

    output_csv,

    index=False,

    encoding="utf-8-sig"

)


print()
print(
    "CSV saved:"
)

print(
    output_csv
)


# ================================================================
# 25. TOP 5 STATIONS
# ================================================================

top5 = (

    station_rain

    .sort_values(

        "total_rain",

        ascending=False

    )

    .head(5)

    .reset_index(drop=True)

)


# ================================================================
# 26. MAXIMUM STATION
# ================================================================

max_station = station_rain.loc[

    station_rain[
        "total_rain"
    ].idxmax()

]


max_station_name = str(

    max_station[
        "station"
    ]

).strip()


max_station_lat = float(

    max_station[
        "latitude"
    ]

)


max_station_lon = float(

    max_station[
        "longitude"
    ]

)


max_station_value = float(

    max_station[
        "total_rain"
    ]

)


print()
print("=" * 70)

print(
    "MAXIMUM RAINFALL"
)

print("=" * 70)

print(
    "Station:",
    max_station_name
)

print(
    f"Rainfall: {max_station_value:.1f} mm"
)

print("=" * 70)


# ================================================================
# 27. LOAD TAMIL NADU SHAPEFILE
# ================================================================

print()
print(
    "Loading Tamil Nadu boundary..."
)


tn_boundary = gpd.read_file(

    shapefile_path

)


print(
    f"District features: {len(tn_boundary)}"
)


# ================================================================
# 28. CRS
# ================================================================

if tn_boundary.crs is not None:

    if tn_boundary.crs.to_epsg() != 4326:

        tn_boundary = tn_boundary.to_crs(
            epsg=4326
        )


# ================================================================
# 29. UNION DISTRICTS
# ================================================================

try:

    tn_union = (
        tn_boundary.geometry.union_all()
    )

except Exception:

    tn_union = (
        tn_boundary.geometry.unary_union
    )


# ================================================================
# 30. STATION ARRAYS
# ================================================================

station_lon = (

    station_rain[
        "longitude"
    ].values.astype(float)

)


station_lat = (

    station_rain[
        "latitude"
    ].values.astype(float)

)


station_values = (

    station_rain[
        "total_rain"
    ].values.astype(float)

)


if len(station_values) < 3:

    raise RuntimeError(
        "At least 3 rainfall stations are required."
    )


# ================================================================
# 31. MAP EXTENT
# ================================================================

minx, miny, maxx, maxy = (

    tn_boundary.total_bounds

)


buffer_x = (
    maxx - minx
) * 0.015


buffer_y = (
    maxy - miny
) * 0.015


minx -= buffer_x
maxx += buffer_x

miny -= buffer_y
maxy += buffer_y


# ================================================================
# 32. CREATE GRID
# ================================================================

grid_x = np.linspace(

    minx,

    maxx,

    GRID_NX

)


grid_y = np.linspace(

    miny,

    maxy,

    GRID_NY

)


grid_lon, grid_lat = np.meshgrid(

    grid_x,

    grid_y

)


# ================================================================
# 33. IDW INTERPOLATION
# ================================================================

print()
print(
    "Running IDW interpolation..."
)


station_points = np.column_stack(

    (
        station_lon,
        station_lat
    )

)


grid_points = np.column_stack(

    (
        grid_lon.ravel(),
        grid_lat.ravel()
    )

)


tree = cKDTree(

    station_points

)


k_value = min(

    IDW_K,

    len(station_points)

)


distances, indices = tree.query(

    grid_points,

    k=k_value

)


if k_value == 1:

    distances = distances[:, np.newaxis]

    indices = indices[:, np.newaxis]


distances = np.maximum(

    distances,

    1e-10

)


weights = (

    1.0 /

    (

        distances ** IDW_POWER

    )

)


weighted_values = (

    np.sum(

        weights *

        station_values[indices],

        axis=1

    )

    /

    np.sum(

        weights,

        axis=1

    )

)


rain_grid = weighted_values.reshape(

    grid_lon.shape

)


# ================================================================
# 34. SMOOTHING
# ================================================================

rain_grid_smooth = gaussian_filter(

    rain_grid,

    sigma=SMOOTH_SIGMA

)


# ================================================================
# 35. TAMIL NADU MASK
# ================================================================

mask = contains_xy(

    tn_union,

    grid_lon,

    grid_lat

)


rain_grid_smooth = np.where(

    mask,

    rain_grid_smooth,

    np.nan

)


# ================================================================
# 36. LIMIT RAINFALL TO 0–300 MM
# ================================================================

plot_grid = np.clip(

    rain_grid_smooth,

    RAIN_MIN,

    RAIN_MAX

)


# ================================================================
# 37. IMPORTANT:
# 0–5 MM WILL NOW BE PURE WHITE
# ================================================================
#
# BoundaryNorm assigns:
#
# 0 <= value < 5       WHITE
# 5 <= value < 10      LIGHT GREEN
# etc.
#
# ================================================================


# ================================================================
# 38. A4 PORTRAIT FIGURE
# ================================================================

A4_WIDTH = 8.27

A4_HEIGHT = 11.69


fig = plt.figure(

    figsize=(

        A4_WIDTH,

        A4_HEIGHT

    ),

    dpi=300,

    facecolor="white"

)


# ================================================================
# 39. HEADER
# ================================================================

fig.text(

    0.50,

    0.965,

    "TAMIL NADU ACCUMULATED RAINFALL",

    ha="center",

    va="center",

    fontsize=17,

    fontweight="bold",

    color="black"

)


fig.text(

    0.50,

    0.941,

    f"{start_date}  TO  {end_date}",

    ha="center",

    va="center",

    fontsize=10,

    fontweight="bold",

    color="#333333"

)


fig.text(

    0.50,

    0.920,

    "TN-SMART MANUAL RAIN GAUGE NETWORK",

    ha="center",

    va="center",

    fontsize=7,

    color="#666666"

)


# ================================================================
# 40. MAP AXIS
# ================================================================

ax = fig.add_axes(

    [

        0.075,

        0.315,

        0.690,

        0.570

    ]

)


# ================================================================
# 41. RAINFALL MAP
# ================================================================

rain = ax.pcolormesh(

    grid_lon,

    grid_lat,

    plot_grid,

    cmap=rain_cmap,

    norm=rain_norm,

    shading="nearest",

    rasterized=True

)


# ================================================================
# 42. DISTRICT BOUNDARIES
# ================================================================

tn_boundary.boundary.plot(

    ax=ax,

    color="black",

    linewidth=0.60,

    zorder=5

)


# ================================================================
# 43. FIND DISTRICT FIELD
# ================================================================

district_field = None


for field in tn_boundary.columns:

    field_lower = str(
        field
    ).lower()


    if field_lower in [

        "dtname",

        "district",

        "district_name",

        "districtname"

    ]:

        district_field = field

        break


print(
    "District field:",
    district_field
)


# ================================================================
# 44. DISTRICT LABELS
# ================================================================

if district_field is not None:

    for _, row in tn_boundary.iterrows():

        try:

            point = (

                row.geometry
                .representative_point()

            )


            district_name = str(

                row[
                    district_field
                ]

            ).strip()


            if district_name == "":

                continue


            txt = ax.text(

                point.x,

                point.y,

                district_name,

                fontsize=4.0,

                color="black",

                ha="center",

                va="center",

                zorder=10

            )


            txt.set_path_effects([

                pe.withStroke(

                    linewidth=1.7,

                    foreground="white",

                    alpha=0.90

                )

            ])


        except Exception:

            continue


# ================================================================
# 45. MAXIMUM RAINFALL STAR
# ================================================================

ax.scatter(

    max_station_lon,

    max_station_lat,

    marker="*",

    s=190,

    facecolor="white",

    edgecolor="black",

    linewidth=1.3,

    zorder=30

)


# ================================================================
# 46. MAXIMUM LABEL
# ================================================================

ax.annotate(

    f"MAXIMUM\n{max_station_value:.1f} mm",

    xy=(

        max_station_lon,

        max_station_lat

    ),

    xytext=(

        12,

        12

    ),

    textcoords="offset points",

    fontsize=7,

    fontweight="bold",

    color="black",

    ha="left",

    va="bottom",

    zorder=35,

    bbox=dict(

        boxstyle="round,pad=0.35",

        facecolor="white",

        edgecolor="black",

        linewidth=0.8,

        alpha=0.96

    ),

    arrowprops=dict(

        arrowstyle="-",

        color="black",

        linewidth=0.7

    )

)


# ================================================================
# 47. MAP EXTENT
# ================================================================

ax.set_xlim(

    minx,

    maxx

)


ax.set_ylim(

    miny,

    maxy

)


ax.set_aspect(

    "equal",

    adjustable="box"

)


# ================================================================
# 48. COORDINATE FORMAT
# ================================================================

def longitude_formatter(
    x,
    pos
):

    return f"{x:.0f}°E"


def latitude_formatter(
    y,
    pos
):

    return f"{y:.0f}°N"


ax.xaxis.set_major_formatter(

    FuncFormatter(

        longitude_formatter

    )

)


ax.yaxis.set_major_formatter(

    FuncFormatter(

        latitude_formatter

    )

)


# ================================================================
# 49. MAP TICKS
# ================================================================

ax.set_xticks(

    np.arange(

        76,

        81,

        1

    )

)


ax.set_yticks(

    np.arange(

        8,

        15,

        1

    )

)


ax.tick_params(

    axis="both",

    labelsize=6,

    length=3,

    width=0.6

)


# ================================================================
# 50. GRID
# ================================================================

ax.grid(

    True,

    linestyle="--",

    linewidth=0.30,

    color="gray",

    alpha=0.25,

    zorder=2

)


# ================================================================
# 51. MAP BORDER
# ================================================================

for spine in ax.spines.values():

    spine.set_linewidth(1.0)

    spine.set_edgecolor("black")


# ================================================================
# 52. RIGHT-SIDE PANEL
# ================================================================

panel_x = 0.790

panel_y = 0.315

panel_w = 0.165

panel_h = 0.570


# ================================================================
# 53. PANEL
# ================================================================
#
# VERY IMPORTANT:
#
# zorder = -10
#
# This keeps the panel behind the colour bar.
#
# ================================================================

panel = FancyBboxPatch(

    (

        panel_x,

        panel_y

    ),

    panel_w,

    panel_h,

    transform=fig.transFigure,

    boxstyle="round,pad=0.005",

    facecolor="#FAFAFA",

    edgecolor="#AFAFAF",

    linewidth=0.8,

    zorder=-10

)


fig.add_artist(

    panel

)


# ================================================================
# 54. MAXIMUM TITLE
# ================================================================

fig.text(

    panel_x + panel_w / 2,

    0.855,

    "MAXIMUM",

    ha="center",

    va="center",

    fontsize=7,

    fontweight="bold",

    color="#555555",

    zorder=20

)


# ================================================================
# 55. MAXIMUM VALUE
# ================================================================

fig.text(

    panel_x + panel_w / 2,

    0.828,

    f"{max_station_value:.1f} mm",

    ha="center",

    va="center",

    fontsize=12,

    fontweight="bold",

    color="black",

    zorder=20

)


# ================================================================
# 56. MAXIMUM DESCRIPTION
# ================================================================

fig.text(

    panel_x + panel_w / 2,

    0.805,

    "★ Highest accumulated rainfall",

    ha="center",

    va="center",

    fontsize=4.8,

    color="#555555",

    zorder=20

)


# ================================================================
# 57. RAINFALL LEGEND TITLE
# ================================================================

fig.text(

    panel_x + panel_w / 2,

    0.770,

    "RAINFALL",

    ha="center",

    va="center",

    fontsize=8,

    fontweight="bold",

    color="black",

    zorder=20

)


fig.text(

    panel_x + panel_w / 2,

    0.752,

    "ACCUMULATED (mm)",

    ha="center",

    va="center",

    fontsize=5.5,

    color="#555555",

    zorder=20

)


# ================================================================
# 58. COLOUR BAR AXIS
# ================================================================
#
# zorder = 50
#
# This guarantees that the colour bar stays visible.
#
# ================================================================

legend_ax = fig.add_axes(

    [

        0.815,

        0.425,

        0.040,

        0.310

    ],

    zorder=50

)


# ================================================================
# 59. CREATE COLOUR BAR
# ================================================================

cbar = fig.colorbar(

    rain,

    cax=legend_ax,

    orientation="vertical",

    boundaries=rain_breaks,

    ticks=rain_breaks,

    spacing="proportional"

)


# ================================================================
# 60. COLOUR BAR LABELS
# ================================================================

cbar.set_ticks(

    [

        0,
        5,
        10,
        25,
        50,
        75,
        100,
        125,
        150,
        175,
        200,
        225,
        250,
        275,
        300

    ]

)


cbar.ax.set_yticklabels(

    [

        "0",
        "5",
        "10",
        "25",
        "50",
        "75",
        "100",
        "125",
        "150",
        "175",
        "200",
        "225",
        "250",
        "275",
        "300"

    ]

)


# ================================================================
# 61. COLOUR BAR TICKS
# ================================================================

cbar.ax.tick_params(

    axis="y",

    labelsize=5.5,

    length=3,

    width=0.7,

    direction="out",

    colors="black"

)


# ================================================================
# 62. COLOUR BAR BORDER
# ================================================================

cbar.outline.set_linewidth(

    1.0

)

cbar.outline.set_edgecolor(

    "black"

)


# ================================================================
# 63. WHITE 0–5 MM CLASS BORDER
# ================================================================
#
# Make the white class clearly visible even on the white panel.
#
# ================================================================

legend_ax.axhline(

    5,

    color="black",

    linewidth=0.4,

    alpha=0.6

)


# ================================================================
# 64. LEGEND DESCRIPTION
# ================================================================

fig.text(

    panel_x + panel_w / 2,

    0.405,

    "Rainfall amount",

    ha="center",

    va="center",

    fontsize=5.5,

    color="#555555",

    zorder=20

)


# ================================================================
# 65. MAP DESCRIPTION
# ================================================================

fig.text(

    0.075,

    0.282,

    "Accumulated rainfall distribution derived from "
    "TN-SMART Manual rain-gauge observations.",

    ha="left",

    va="center",

    fontsize=5.8,

    color="#555555"

)


# ================================================================
# 66. TOP 5 TITLE
# ================================================================

fig.text(

    0.075,

    0.225,

    "TOP 5 ACCUMULATED RAINFALL STATIONS",

    ha="left",

    va="center",

    fontsize=8.5,

    fontweight="bold",

    color="black"

)


# ================================================================
# 67. TOP 5 TABLE AXIS
# ================================================================

bottom_table_ax = fig.add_axes(

    [

        0.075,

        0.105,

        0.850,

        0.105

    ]

)


bottom_table_ax.axis(
    "off"
)


# ================================================================
# 68. TOP 5 TABLE DATA
# ================================================================

bottom_data = []


for i, row in top5.iterrows():

    station_name = str(

        row["station"]

    ).strip()


    location_name = str(

        row["location"]

    ).strip()


    if len(station_name) > 38:

        station_name = (

            station_name[:37]

            + "..."

        )


    if len(location_name) > 30:

        location_name = (

            location_name[:29]

            + "..."

        )


    bottom_data.append(

        [

            str(i + 1),

            station_name,

            location_name,

            f"{row['total_rain']:.1f} mm"

        ]

    )


# ================================================================
# 69. CREATE TOP 5 TABLE
# ================================================================

bottom_table = bottom_table_ax.table(

    cellText=bottom_data,

    colLabels=[

        "RANK",

        "RAIN GAUGE STATION",

        "LOCATION",

        "ACCUMULATED RAINFALL"

    ],

    colWidths=[

        0.10,

        0.42,

        0.26,

        0.22

    ],

    cellLoc="left",

    colLoc="left",

    loc="center"

)


bottom_table.auto_set_font_size(

    False

)


bottom_table.set_fontsize(

    6

)


bottom_table.scale(

    1,

    1.40

)


# ================================================================
# 70. TABLE STYLE
# ================================================================

for (

    row_index,

    col_index

), cell in bottom_table.get_celld().items():

    cell.set_edgecolor(

        "#B8B8B8"

    )

    cell.set_linewidth(

        0.45

    )


    if row_index == 0:

        cell.set_facecolor(

            "#E6E9EB"

        )

        cell.set_text_props(

            weight="bold",

            color="black"

        )

    else:

        cell.set_facecolor(

            "white"

        )


# ================================================================
# 71. FOOTER
# ================================================================

fig.text(

    0.075,

    0.072,

    "Source: TN-SMART Rain Gauge Stations",

    ha="left",

    va="center",

    fontsize=5.8,

    color="#555555"

)


fig.text(

    0.075,

    0.056,

    "Spatial interpolation: Inverse Distance Weighting (IDW)",

    ha="left",

    va="center",

    fontsize=5.5,

    color="#777777"

)


fig.text(

    0.925,

    0.064,

    f"Maximum: {max_station_value:.1f} mm",

    ha="right",

    va="center",

    fontsize=6.5,

    fontweight="bold",

    color="black"

)


# ================================================================
# 72. A4 PAGE BORDER
# ================================================================

page_border = Rectangle(

    (

        0.018,

        0.018

    ),

    0.964,

    0.964,

    transform=fig.transFigure,

    fill=False,

    edgecolor="black",

    linewidth=1.0,

    zorder=100

)


fig.add_artist(

    page_border

)


# ================================================================
# 73. SAVE PNG
# ================================================================

print()
print("=" * 70)

print(
    "SAVING PROFESSIONAL A4 MAP..."
)

print("=" * 70)


plt.savefig(

    output_png,

    dpi=300,

    facecolor="white",

    edgecolor="white",

    bbox_inches=None,

    pad_inches=0

)


# ================================================================
# 74. CLOSE FIGURE
# ================================================================

plt.close(

    fig

)


# ================================================================
# 75. VERIFY IMAGE
# ================================================================

try:

    check_image = Image.open(

        output_png

    )


    width_px, height_px = (

        check_image.size

    )


    print()
    print("=" * 70)

    print(
        "OUTPUT VERIFICATION"
    )

    print("=" * 70)

    print(
        f"Width  : {width_px} pixels"
    )

    print(
        f"Height : {height_px} pixels"
    )

    print()

    print(
        "Expected A4 at 300 DPI:"
    )

    print(
        "2481 × 3507 pixels"
    )

    print()

    print(
        "Output:"
    )

    print(
        output_png
    )

    print("=" * 70)


except Exception as e:

    print(
        "Image verification failed:"
    )

    print(e)


# ================================================================
# 76. FINAL SUMMARY
# ================================================================

print()
print("=" * 70)

print(
    "RAIN FALL MAP COMPLETED"
)

print("=" * 70)

print()

print(
    f"Period: {start_date} to {end_date}"
)

print()

print(
    f"Maximum station: {max_station_name}"
)

print()

print(
    f"Maximum rainfall: {max_station_value:.1f} mm"
)

print()

print(
    "0–5 mm colour: WHITE"
)

print(
    "5–10 mm colour: LIGHT GREEN"
)

print(
    "Legend range: 0–300 mm"
)

print(
    "Station IDs on map: NO"
)

print(
    "Station dots on map: NO"
)

print(
    "Maximum STAR: YES"
)

print(
    "Top 5 table: YES"
)

print(
    "Latitude/Longitude in table: NO"
)

print(
    "Layout: A4 PORTRAIT"
)

print(
    "Resolution: 300 DPI"
)

print()

print(
    "PNG:"
)

print(
    output_png
)

print()

print(
    "CSV:"
)

print(
    output_csv
)

print()

print("=" * 70)
