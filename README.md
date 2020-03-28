**FLIGHT PRICES TRACKER**

**PURPOSE**: Return cheapest flight from the Skyskanner using custom parameters (city from/to, date etc.)

**PREREQUISITES (for running on own machine)**:
1. *Up and running MongoDB server* 
  (db and collection created automatically if missing)
2. *Created general API key on rapidapi.com* 
   (https://docs.rapidapi.com/docs/keys)
3. *Created 'config_private_keys.py'* 
   Content: rapidapi_key = "SECRET_API_KEY"
3. *Installed libraries*:
   - pymongo
   - colorama
   - send2trash
   - json
   - sys
   - requests
   - bson
   - logging

**HOW TO RUN**:
1. Change parameters in config.py to custom if needed
2. Run runner.py

**PROGRAM MODE:**
Generally program can be run in either mode:
- __Live API__ - up to date latest data from Skyskanner (https://skyscanner.github.io/slate/#flights-live-prices).
*It's more time and resource consuming, returns ALL flights for the passed parameters.*
- __Browse Quotes__ - flight with min price from the Skyskanner cache (https://skyscanner.github.io/slate/#browse-quotes)
*It runs much faster than previous call, returns 1 flight with min price for the passed parameters.*
To chose mode, please set 'live_api_mode' to True or False.

**PROCESS FLOW**:
1. __Get airport city ids__ from city names (departure & destination)
2. __Create Live Pricing Service Session__ (it should be created before requesting Live price data) 
   __and get results from Live API__ OR __get results from Browse Quotes__ 
4. __Record JSON into MondoDB__
5. __Retry__ if process fails at any of the points above
6. __Record JSON into file__ if passed respective flag (for test purposes)
7. __Repeat process for N days__ (pickle date in case process was interrupted, so it's possible to continue
   where it left off)
8. __Find cheapest flight__ (or with price lower than threshold for Live API)
