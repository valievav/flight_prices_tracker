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

**PROCESS FLOW**:
1. Get airport city ids from city names (departure & destination)
2. Create Live Pricing Service Session (it should be created before requesting Live price data,
   more details at https://skyscanner.github.io/slate/#flights-live-prices)
3. Get results from Live API
4. Record JSON from the response into MondoDB
5. Record JSON from the response into file if passed respective flag (for test purposes)
6. Retry if process fails at any of the 5 points above
7. Repeat process for N days (pickle date in case process was interrupted, so it's possible to continue
   where it left off)
8. Find flights with price lower than threshold
