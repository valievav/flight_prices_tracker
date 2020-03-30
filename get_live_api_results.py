"""
Contains methods for Live API import.
Live API retrieval consists of 2 parts: creating session and getting results.
"""

import json
import logging
import requests
from service_methods import timer, retry


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

