"""
Contains methods for Live API import.
Live API retrieval consists of 2 parts: creating session and getting results.
"""

import datetime
import json
import logging
import os
import pickle
import sys
import pymongo
import requests
from bson import json_util  # to record JSON to file after mongodb
from mongodb_methods import record_json_to_mongodb
from service_methods import timer, retry


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
                logger.debug(f"{stage_name} - Available codes for {search_city}-{search_country}: {location_airport_ids}. "
                             f"Going to use 1st element from the list.")
                logger.info(f"{stage_name} - {search_city}-{search_country} airport id - '{airport_id}'")
                return airport_id


def live_prices_create_session(base_url: str, headers: dict, cabin_class: str, country: str, currency: str,
                               locale_lang: str, origin_place: str, destination_place: str, outbound_date: str,
                               adults_count: int, max_retries: int, logger: logging.Logger)-> str:
    """
     Creates Live Pricing Service Session (it should be created before requesting price data).\n
     See detailed documentation -> https://skyscanner.github.io/slate/#flights-live-prices
    """

    stage_name = "CREATE_SESSION"
    try_number = 0

    url = f"{base_url}pricing/v1.0"
    payload = f"cabinClass={cabin_class}&country={country}&currency={currency}" \
              f"&locale={locale_lang}&originPlace={origin_place}&destinationPlace={destination_place}" \
              f"&outboundDate={outbound_date}&adults={adults_count}"
    headers.setdefault('content-type', "application/x-www-form-urlencoded")

    # rerun if response unsuccessful
    while True:
        try:
            response = requests.request("POST", url, data=payload, headers=headers)
            logger.debug(f"{stage_name} - Full requested url: {url}/{payload}")
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            try_number += 1
            retry(stage_name, try_number, max_retries, err, logger=logger)
        else:
            session_key = response.headers["Location"].split("/")[-1]
            logger.info(f"{stage_name} - Session created successfully")
            return session_key


def live_prices_pull_results(base_url: str, headers: dict, session_key: str,
                             max_retries: int, logger: logging.Logger) -> list:
    """
    Returns Live API results from the created session.
    """

    stage_name = "PULL_RESULTS"
    try_number = 0

    url = f"{base_url}pricing/uk2/v1.0/{session_key}?pageIndex=0&pageSize=20"
    querystring = {"pageIndex": "0", "pageSize": "100"}
    all_results = []

    # rerun if response unsuccessful
    while True:
        response = requests.request("GET", url, headers=headers, params=querystring)
        result = json.loads(response.text)

        if response.status_code == 200:
            all_results.append(result)
            if result["Status"] == "UpdatesPending":  # get next scope results
                logger.info(f"{stage_name} - Got response 'UpdatesPending'. Requesting more results after delay.")
                timer(wait_time=10, logger=logger)  # wait for all results to be updated
                continue
            logger.info(f'{stage_name} - Got response status - {result["Status"]}. '
                        f'Recorded {len(all_results)} result requests.')
            break
        else:
            try_number += 1
            retry(stage_name, try_number, max_retries, f"{response.status_code} - {response.content}", logger=logger)

    return all_results


def get_live_api_results(base_url: str, headers: dict, cabin_class: str, country: str, currency: str,
                         locale_lang: str, airport_id_orig: str, airport_id_dest: str, outbound_date: str,
                         adults_count: int, max_retries: int, logger: logging.Logger)-> iter:
    """
    Performs 2 steps to get Live API results: creates Live API session and retrieves API results
    """

    # create session
    session_key = live_prices_create_session(base_url=base_url,
                                             headers=headers,
                                             cabin_class=cabin_class,
                                             country=country,
                                             currency=currency,
                                             locale_lang=locale_lang,
                                             origin_place=airport_id_orig,
                                             destination_place=airport_id_dest,
                                             outbound_date=outbound_date,
                                             adults_count=adults_count,
                                             max_retries=max_retries,
                                             logger=logger)

    # retrieve results
    all_results = live_prices_pull_results(base_url=base_url,
                                           headers=headers,
                                           session_key=session_key,
                                           max_retries=max_retries,
                                           logger=logger)

    return all_results


def get_browse_quotes(base_url: str, headers: dict, country: str, currency: str,
                      locale_lang: str, airport_id_orig: str, airport_id_dest: str,
                      outbound_date: str, max_retries: int, logger: logging.Logger)-> list:
    """
    Runs Browse Quotes API call, which retrieves the cheapest quotes from Skyskanner cache prices
    """

    stage_name = "CACHED_QUOTE"
    try_number = 0

    url = f"{base_url}browsequotes/v1.0/{country}/{currency}/{locale_lang}/{airport_id_orig}/{airport_id_dest}/{outbound_date}"
    all_results = []

    # rerun if response unsuccessful
    while True:
        response = requests.request("GET", url, headers=headers)
        result = json.loads(response.text)

        if response.status_code == 200 and len(result) != 0:
            logger.info(f'{stage_name} - Received result.')
            all_results.append(result)
            return all_results
        else:
            try_number += 1
            retry(stage_name, try_number, max_retries, f"{response.status_code} - {response.content}", logger=logger)


def record_results_into_file(file_folder_path: str, file_name: str, results: iter, logger: logging.Logger)-> None:
    """
    Records dict into json file
    """

    stage_name = "RECORD_RESULTS_INTO_FILE"

    # create files folder if not exists
    if not os.path.exists(file_folder_path):
        os.mkdir(file_folder_path)
    file_abs_path = os.path.join(file_folder_path, file_name)

    while True:
        try:
            with open(file_abs_path, "w") as file:
                # json_util encoder after pymongo (else "not JSON serializable" error)
                json.dump(results, indent=4, fp=file, default=json_util.default)
            logger.info(f"{stage_name} - Recorded results into '{file_abs_path.split(os.path.sep)[-1]}'.")
            return
        except Exception as exc:
            logger.warning(f"{stage_name} - Could'n record data into file, occurred exception - '{exc}")


def pickle_data(file_name: str, data_to_pickle: iter, logger: logging.Logger) -> None:
    """
    Creates new file with pickled data is not exists else updates it
    """

    stage_name = "PICKLE DATA"

    # record new file or update existing
    with open(file_name, "wb") as file:
        pickle.dump(data_to_pickle, file, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"{stage_name} - '{file_name}' content: {data_to_pickle}")


def unpickle_data(file_name: str, logger: logging.Logger) -> iter:
    """
    Retrieves pickled data from file
    """

    stage_name = "UNPICKLE DATA"

    # retrieve pickled data if exists
    try:
        with open(file_name, "rb") as file:
            data = pickle.load(file)
            logger.debug(f"{stage_name} - Unpickled {data} from '{file_name}'")
            return data
    except FileNotFoundError:
        logger.warning(f"{stage_name} - Pickled file is not found")


def get_api_data_for_n_days(days: int, pickle_file: str, base_url: str, headers: dict, cabin_class: str,
                            country: str, currency: str, locale_lang: str, city_from: str, city_to: str,
                            country_from: str, country_to: str, outbound_date: str, adults_count: int, max_retries: int,
                            json_files_folder: str, json_file: str, collection: pymongo.collection.Collection,
                            live_api_mode: bool, logger: logging.Logger, save_to_file: bool = False)-> None:
    """
    Gets airport origin and destination IDs, gets Live API results (all flights, up to date)
    or Browse Quotes (one cheapest flight from the cache) for N days,
    pickles last used date (to continue where left off in case of interruption),
    records data to MongoDB and into file (depends on the flag).
    """

    # log the mode program is running in
    logger.info(f"PROGRAM IS RUNNING IN MODE ->> "
                f"{'LIVE API (getting most recent data)' if live_api_mode else 'BROWSE QUOTES (getting cached data)'}")

    for n in range(days):

        # get outbound date from picked file (to continue where left off) or use passed date
        pickled_data = unpickle_data(file_name=pickle_file,
                                     logger=logger)

        outbound_date = pickled_data[f"{city_from}-{city_to}"] if pickled_data else outbound_date
        logger.info(f"Running API request for -> {outbound_date}")
        outbound_date_datetime = datetime.datetime.strptime(outbound_date, "%Y-%m-%d").date()

        # check date validity before run
        if datetime.datetime.now().date() > outbound_date_datetime:
            sys.exit(f"Outbound date {outbound_date_datetime} is in the past. Please fix.")

        # get airport IDs origin & destination
        airport_id_orig = get_airport_id(base_url=base_url,
                                         headers=headers,
                                         currency=currency,
                                         locale_lang=locale_lang,
                                         search_city=city_from,
                                         search_country=country_from,
                                         max_retries=max_retries,
                                         logger=logger)

        airport_id_dest = get_airport_id(base_url=base_url,
                                         headers=headers,
                                         currency=currency,
                                         locale_lang=locale_lang,
                                         search_city=city_to,
                                         search_country=country_to,
                                         max_retries=max_retries,
                                         logger=logger)

        # get LIVE API results OR Browse Quotes
        if live_api_mode:
            all_results = get_live_api_results(base_url=base_url,
                                               headers=headers,
                                               cabin_class=cabin_class,
                                               country=country,
                                               currency=currency,
                                               locale_lang=locale_lang,
                                               airport_id_orig=airport_id_orig,
                                               airport_id_dest=airport_id_dest,
                                               outbound_date=outbound_date,
                                               adults_count=adults_count,
                                               max_retries=max_retries,
                                               logger=logger)
        else:
            all_results = get_browse_quotes(base_url=base_url,
                                            headers=headers,
                                            country=country,
                                            currency=currency,
                                            locale_lang=locale_lang,
                                            airport_id_orig=airport_id_orig,
                                            airport_id_dest=airport_id_dest,
                                            outbound_date=outbound_date,
                                            max_retries=max_retries,
                                            logger=logger)

        # record results into db
        record_json_to_mongodb(json_data=all_results,
                               collection=collection,
                               max_retries=max_retries,
                               logger=logger)

        # record results into file
        if save_to_file:
            file_folder_path = os.path.join(os.getcwd(), json_files_folder)
            file_name = json_file.replace('xxx', outbound_date)
            record_results_into_file(file_folder_path=file_folder_path,
                                     file_name=file_name,
                                     results=all_results,
                                     logger=logger)
        # find next date
        next_outbound_date_datetime = outbound_date_datetime + datetime.timedelta(days=1)
        outbound_date = next_outbound_date_datetime.strftime("%Y-%m-%d")

        # pickle next date (process can resume from this point on the next run)
        pickle_data(file_name=pickle_file,
                    data_to_pickle={f"{city_from}-{city_to}": outbound_date},
                    logger=logger)

