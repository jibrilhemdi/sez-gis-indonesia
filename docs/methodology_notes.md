# Acquisition methodology

ArcGIS tables are fetched by a frozen server-side list of object IDs, in batches within the advertised record limit. Raw API responses, request parameters, and layer metadata are retained. A final count and data edit timestamp are compared with the initial snapshot. A changed service invalidates reconciliation and is flagged for review.

Current port locations are never assigned a 1992 geometry date. Missing historical evidence yields `unknown`, not absence. Dates retain their original precision. Peat unknown pixels and missing islands must remain unknown. GEBCO signed elevation and categorical TID are retained without conversion into navigational depths or uncertainty scores.

The proposed grid is optional. No grid feature is computed until supported layers and treatment geometry are verified.

The GEBCO_2026 elevation and TID OPeNDAP arrays were extracted from the CEDA URLs linked by the official archive. Each subset includes native pixel centres within 93–143°E, 13°S–8°N, with no resampling. The materialized NetCDF subsets retain source variables and attributes; north-up GeoTIFFs reverse row order only. The 15 arc-second grid spans 5,040 × 12,000 cells. TID is categorical and elevations retain their sign. CEDA DDS/DAS and exact array constraints are kept in raw storage.

The 1996 IAPH table supports presence of seven named container ports in 1991–1995, including 1992 and 1995. OCR errors make the printed quantities unsafe to transcribe automatically, so the derived table records presence only. No continuity beyond 1995 or historical coordinates are inferred.

The published KAPET evaluation by Rothenberg, Wang and Chari (2025) was acquired from the University of Sussex repository and reopened as a 24-page PDF. Its Data availability statement on PDF page 22 says data will be made available on request. The author's publication page lists no replication package for this specific article; adjacent links belong to other papers. This is evidence about the article's stated access route, not proof that a treatment shapefile is available. The 2017 RAND working paper has a different author set and is retained only as a historical reference, not substituted for the published article.
