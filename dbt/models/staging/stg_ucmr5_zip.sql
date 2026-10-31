select distinct
    pwsid,
    zipcode as zip5
from {{ source('raw', 'ucmr5_zipcodes') }}
where pwsid is not null and zipcode is not null
