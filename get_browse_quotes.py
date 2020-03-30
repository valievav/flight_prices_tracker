import logging
import requests
import json
from service_methods import retry


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

