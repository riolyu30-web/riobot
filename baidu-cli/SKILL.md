---
name: "find-location-details"
description: "Get detailed address, nearby places (restaurants, hotels, etc.), and roads from a given location (latitude/longitude). Invoke this when user wants to know 'what is at this location', 'find places near these coordinates', or needs an address for a specific point."
---

# Find Location Details CLI

This skill can find location details for a given latitude/longitude pair. It takes geographic coordinates (latitude and longitude) and returns detailed address information, surrounding Points of Interest (POIs), and nearby roads.


## How to use

Run the python script `baidumap_search.py` directly.

### Basic Usage
```bash
python baidumap_search.py --lat 39.951335 --lng 116.514844
```

### Advanced Usage (with POIs and Roads)
```bash
python baidumap_search.py --lat 39.951335 --lng 116.514844 --extensions-poi 1 --radius 2000 --poi-types "酒店|美食" --extensions-road true
```

## Command Line Options

| Option | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--lat` | `FLOAT` | **Yes** | None | Latitude (e.g., 39.951335) |
| `--lng` | `FLOAT` | **Yes** | None | Longitude (e.g., 116.514844) |
| `--poi-types` | `TEXT` | No | `""` | Filters the returned POI types (e.g., '酒店\|房地产'). See `poi_type.md` for full categories. |
| `--extensions-poi` | `TEXT` | No | `"0"` | Set to `"1"` to return POI data and semantic descriptions, `"0"` to not return them. |
| `--radius` | `INTEGER` | No | `1000` | POI search radius in meters. Range: 0-3000. |
| `--extensions-road` | `TEXT` | No | `"false"` | Set to `"true"` to return the 3 nearest roads around the coordinates. |
| `--region-data-source` | `INTEGER`| No | `2` | Source of administrative division data: `1` (Statistics Bureau), `2` (Civil Affairs Bureau). |
| `--entire-poi` | `INTEGER` | No | `0` | Set to `1` to recall more POIs and optimize the address result. |
| `--sort-strategy` | `TEXT` | No | `"distance"` | POI sorting strategy: `distance`, `rank`, or `default`. |
| `--coordtype` | `TEXT` | No | `"bd09ll"` | The coordinate type of the input: `bd09ll` (Baidu lat/lng), `gcj02ll` (National), `wgs84ll` (GPS), etc. |
| `--ret-coordtype` | `TEXT` | No | `"bd09ll"` | The coordinate type of the output: `bd09ll` or `gcj02ll`. |
| `--sn` | `TEXT` | No | `""` | Required only if the AK uses SN signature validation. |
| `--output` | `TEXT` | No | `"json"` | Output format: `json` or `xml`. |
| `--callback` | `TEXT` | No | `""` | JavaScript callback function name for JSONP functionality. |
| `--language` | `TEXT` | No | `"zh-CN"` | Language of the returned parameters (e.g., `zh-CN`, `en`). |
| `--language-auto` | `INTEGER`| No | `0` | Set to `1` to auto-fill missing administrative divisions in the specified language, `0` to disable. |


To view the full list of supported POI categories and subcategories, you can read the `poi_type.md` file use `read_file` command
