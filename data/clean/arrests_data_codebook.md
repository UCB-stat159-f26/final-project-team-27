# Arrests data codebook

Authors of this codebook: Urwa Irfan, Melanie T. Huynh, Anh Tran

Updated November 27, 2026.

*The descriptions below reflect our interpretation of the published field names, the source dataset, and the preprocessing performed for this project.*

This codebook describes `arrests_data.csv`, produced by `scripts/arrests_data_processing.py`.

| **File Name** | **Data Name** | **Source** | **Data Structure** |
|----|----|----|----|
| `arrests_2016_current.csv` | Berkeley PD Cases 2016 to Current | [Berkeley Police Department source table](https://services7.arcgis.com/vIHhVXjE1ToSg0Fz/arcgis/rest/services/Berkeley_PD_Cases_2016_to_Current/FeatureServer/0) | CSV |

Each output row retains one record from the published cases table. Multiple rows can share the same `Case_Number`. `ObjectId` identifies the source-table record.

All original columns are retained in their original order. The `Occurred_Datetime` values are converted to Pacific time and formatted consistently. Source rows retain their original order.

Empty CSV cells represent missing values. Literal source labels, including `"None"` in `Statute_Type`, are preserved as text.

| **Column Title** | **Data Type** | **Data Description** |
|----|----|----|
| `Case_Number` | `string` | Berkeley Police Department case identifier. Multiple source records can share a case number. |
| `Occurred_Datetime` | `string` | Occurrence timestamp converted from the published UTC timestamp to `America/Los_Angeles`, formatted as `%Y-%m-%d %H:%M:%S%z`. |
| `Incident_Type` | `string` | Incident category supplied in the source record. |
| `Statute` | `string` | Statute or code reference associated with the record. |
| `Statute_Description` | `string` | Source description associated with the statute or code reference. |
| `Statute_Type` | `string` | Source category identifying the applicable code or statutory system. Observed categories are listed below. |
| `Block_Address` | `string` | Location description supplied by the source, including block addresses and intersections. Missing addresses are retained. |
| `City` | `string` | Event city supplied by the source. Retained records match `BERKELEY` after trimming whitespace and normalizing capitalization for comparison. |
| `ZIP_Code` | `string` | ZIP code supplied by the source, retained as an identifier. |
| `ObjectId` | `string` | Source-table record identifier, retained for traceability. |

**Preprocessing rules**
- Records are retained when the event city matches `BERKELEY` after whitespace trimming and case normalization.
- The cutoff is evaluated using Berkeley calendar dates in `America/Los_Angeles`.
- The inclusive lower bound is 1 March 2021 at 00:00:00 Pacific time.
- The exclusive upper bound is 1 May 2026 at 00:00:00 Pacific time. This includes all of 30 April 2026.
- Published timestamps are parsed using their UTC offset before conversion to Pacific time.
- Missing or unparseable timestamps are excluded.
- The output datetime format is `%Y-%m-%d %H:%M:%S%z`.
- Pacific offsets follow daylight saving time, using `-0800` during standard time and `-0700` during daylight saving time.
- Rows with missing `Block_Address` values remain in the output.
- Repeated case numbers and repeated source records are retained.
- Berkeley membership in this preprocessing step is determined by the source `City` field.
- Location descriptions and coordinates are handled by the separate spatial preprocessing workflow.

**`Statute_Type` categories observed in the processed data**
- Penal Code
- Vehicle Code
- Health and Safety
- Berkeley Municipal Code
- Welfare and Institution
- Business and Professional
- United States
- None

The final category above is the literal source text `"None"`.

**Interpretation**: A row count measures retained source records. A count of distinct `Case_Number` values measures distinct case identifiers.

The datetime conversion follows the UTC reference declared by the published source. The cutoff dates are interpreted as local Berkeley calendar dates.