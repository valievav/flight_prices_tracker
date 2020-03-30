import json
import logging
import sys
import requests
from service_methods import retry


def get_airport_id(base_url: str, headers: dict, currency: str, locale_lang: str,
                   search_city: str, search_country: str, max_retries: int,
                   logger: logging.Logger, element_from_matched_list: int = 0) -> str:
    """
    Gets 1st airport id by default for search city-country combination (1 city-country pair can have several airports).
    """

    stage_name = "GET_PLACE_ID"
    try_number_resp = 0
    try_number_n = 0

    # get airport_id for search city-country pair
    url = f"{base_url}autosuggest/v1.0/{currency}/{currency}/{locale_lang}/"
    querystring = {"query": {search_city}}

    # rerun if response unsuccessful or can't extract n-th element
    while True:
        try:
            response = requests.request("GET", url, headers=headers, params=querystring)
            result = json.loads(response.text)
        except Exception as exc:
            try_number_resp += 1
            retry(stage_name, try_number_resp, max_retries, exc, logger=logger)
        else:
            # get all airport ids
            location_airport_ids = []
            for location_data in result['Places']:
                if location_data['CountryName'].lower() == search_country.lower():
                    location_airport_ids.append(location_data['PlaceId'])

            if not location_airport_ids:
                logger.critical(f"{stage_name} - Place_ids list is empty! Exiting the program.")
                sys.exit()

            # return n-th elem
            try:
                airport_id = location_airport_ids[element_from_matched_list]
            except Exception as exc:
                try_number_n += 1
                retry(stage_name, try_number_n, max_retries, exc, logger=logger)
            else:
                logger.debug(f"{stage_name} - Available codes for {search_city}-{search_country}: {location_airport_ids}."
                             f" Going to use 1st element from the list.")
                logger.info(f"{stage_name} - {search_city}-{search_country} airport id - '{airport_id}'")
                return airport_id
