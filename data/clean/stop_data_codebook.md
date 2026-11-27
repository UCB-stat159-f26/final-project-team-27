# Stop data codebook

Authors of this codebook: Urwa Irfan, Melanie T. Huynh, Anh Tran

Updated November 26, 2026.

*We, the authors, duly note that the data descriptions for describing the contents of the CSV are our interpretations of what the data represents. These descriptions are based on our experiences preprocessing the data for replication and our interpretations of what titles/descriptions originally exist in the dataset.*

This is a codebook for the processed stop data, with filename `stop_data.csv`. The source for the raw data from the Berkeley Police Department's Transparency Hub is described below:

| **File Name** | **Data Name** | **Source** | **Data Structure** | **Upload Date** | **Updated Date** |
|----|----|----|----|----|----|
|`stop_data_2020_2023.csv`|Berkeley PD - Stop Data (October 1, 2020 – December 31, 2023)|[Link](https://bpd-transparency-initiative-berkeleypd.hub.arcgis.com/datasets/35cc0ccb17ba400b93cba5db5a37b140/about)|CSV|December 9, 2022|January 2, 2025|
|`stop_data_2024_current.csv`|Berkeley PD - Stop Data (2024 - Current)|[Link](https://bpd-transparency-initiative-berkeleypd.hub.arcgis.com/datasets/078f7d987228453ca30cf7a99311d8de/about)|CSV|March 21, 2024|June 30, 2025|

Each row of the processed CSV corresponds to a specific stop. Each stop has the associated columns as listed below. `NaN` types do exist as entries in the dataset and are interpreted as missing values. Columns marked with * have a longer list of categories, noted at the end of this file.

| **Column Title** | **Data Type** | **Data Description** |
|----|----|----|
| `LEA_Record_ID` | `string` | Local Enforcement Agency (LEA) Record ID, individual stop record ID from Berkeley PD. |
| `PersonNum` | `integer` | Number of people stopped. |
| `DateTimeOfStop` | `string` | Timestamp of the stop, in the format `%Y-%m-%d %H:%M:%S%z`. |
| `StopDuration` | `integer` | Duration of the stop in minutes. |
| `CallForService` | `bool` | Whether the stop was based on a call for service. |
| `TypeOfStopDesc` | `string` | Type of stop description, with 3 categories: vehicular, pedestrian, or bicycle stop. |
| `LocationType` | `string` | How the location of the stop is recorded in the dataset, with 5 cateogies: LatLonPt (i.e., latitude and longitude point), BlkNumber (i.e., street name and block number), Intersection (i.e., two street names), HighwayAndExit, and Other. |
| `Latitude` | `float` | Decimal latitude. Provided if `LocationType` is LatLonPt. |
| `Longitude` | `float` | Decimal longitude. Provided if `LocationType` is LatLonPt. |
| `BlockNumber` | `float` | City block number. Provided if `LocationType` is BlkNumber. |
| `StreetName` | `string` | City street name. Provided if `LocationType` is BlkNumber. |
| `CrossStreet1` | `string` | Cross street 1 name. Provided if `LocationType` is Intersection. |
| `CrossStreet2` | `string` | Cross street 2 name. Provided if `LocationType` is Intersection. |
| `Highway` | `string` | Highway name. Provided if `LocationType` is HighwayAndExit. |
| `ClosestExit` | `string` | Closest exit on the highway. Provided if `LocationType` is HighwayAndExit. |
| `OtherLocationDesc` | `string` | Provided if `LocationType` is Other. |
| `City` | `string` | City name where stop occurred. |
| `TrafficViolationType` | `string` | The type of traffic violation, with 3 categories: equipment, moving, non-moving violation including registration. |
| `NonForceActionsTaken*` | `string` | Any non-force action taken as a result of the stop, with 18 categories. Multiple actions can be included in one stop. NaN if no non-force action taken. |
| `PropertySeized*` | `string` | The property seized, with 11 categories. Multiple categories can be included in one stop. NaN if no property seized. |
| `WeaponsFound` | `bool` | Whether weapons were found with the person stopped. |
| `ForceActionsTaken*` | `string` | Any force action taken as a result of the stop, with 16 categories. Multiple actions can be included in one stop. NaN if no force action taken. |
| `ContrabandOrEvidence*` | `string` | The propery seized if classified as contraband or evidence, with 10 categories. Multiple categories can be included in one stop. NaN if no contraband or evidence seized. |
| `ResultOfStop*` | `string` | The final result of the stop, with 11 categories. Multiple categories can be included in one stop. |
| `WarningOffense` | `string` | The vehicle code name and number violated if `ResultOfStop` includes Verbal or Written warning. NaN otherwise. |
| `CitationForInfractionOffense` | `string` | The vehicle code name and number violated if `ResultOfStop` includes Citation for infraction. NaN otherwise. |
| `InfieldCiteRelOffense` | `string` | The vehicle code name and number violated if `ResultOfStop` includes In-field cite and release. NaN otherwise. |
| `CustodialArrestNoWarrantOffense` | `string` | The vehicle code name and number violated if `ResultOfStop` includes Custodial arrest without warrant. NaN otherwise. |

`NonForceActionsTaken` categories:

* Property was seized
* Patrol car detention
* Terry v. Ohio frisk/pat search of the person’s outer clothing was conducted
* Asked whether the person is on parole
* Person removed from vehicle by order
* or some other form of mandatory supervision
* Search of person was conducted
* Asked for identification of stopped person’s passenger
* Search of property was conducted
* Asked for consent to search person
* Curbside detention
* PRCS
* Ran name of stopped person’s passenger
* probation
* Person photographed
* Asked for consent to search property
* Field sobriety test conducted
* Vehicle impounded

`ForceActionsTaken` categories:

* Use of vehicle in apprehension of stopped person
* Other physical or vehicle contact
* Handcuffed or flex cuffed
* Firearm pointed at person
* Baton or other impact weapon used
* Electronic control device pointed at person or sparked
* Impact projectile weapon pointed at person
* Peace officer's canine bit or held person
* blunt impact projectile
* Person removed from vehicle by physical contact
* Impact projectile discharged or used (e.g.
* Electronic control device used in dart-mode
* rubber bullets or bean bags)
* Physical compliance tactics and techniques
* Firearm discharged
* Baton or other impact weapon drawn
* Firearm unholstered
* Baton or other impact weapon used or other object (including a firearm) to strike or prod

`PropertySeized` categories:

* Other contraband or evidence
* Weapon(s) other than firearm
* Cell phone(s) or electronic devices
* Alcohol
* Drugs/narcotics
* Vehicle
* Money
* Suspected stolen property
* Firearms
* Ammunition
* Drug paraphernalia

`ContrabandOrEvidence` categories:

* Weapon(s) other than a firearm
* Other contraband or evidence
* Cell phone(s) or electronic device(s)
* Alcohol
* Drugs/narcotics
* Money
* Suspected stolen property
* Firearm(s)
* Ammunition
* Drug paraphernalia

`ResultOfStop` categories:

* Custodial arrest without warrant
* No action
* Noncriminal transport or caretaking transport (including transport by officer
* Psychiatric hold (W&I Code 5150 or 5585.20)
* ambulance or other agency)
* Citation for infraction
* Warning (verbal or written)
* Written warning
* In-field cite and release
* Field interview card completed
* Contacted parent/legal guardian or other person responsible for the minor
* Custodial arrest pursuant to outstanding warrant
* Verbal warning
