import datetime
import logging
import os
import pymongo
from get_airport_id import get_airport_id
from get_browse_quotes import get_browse_quotes
from get_live_api_results import get_live_api_results
from mongodb_methods import record_json_to_mongodb
from service_methods import pickle_data, record_results_into_file, get_outbound_date


def get_api_results_for_n_days(days: int, pickle_file: str, base_url: str, headers: dict, cabin_class: str,
                               country: str, currency: str, locale_lang: str, city_from: str, city_to: str,
                               country_from: str, country_to: str, outbound_date: str, adults_count: int,
                               max_retries: int, json_files_folder: str, json_file: str,
                               collection: pymongo.collection.Collection, live_api_mode: bool,
                               logger: logging.Logger, save_to_file: bool = False)-> None:
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
        # define outbound date (use from config or pickle file)
        outbound_date = get_outbound_date(outbound_date_config=outbound_date,
                                          pickle_file=pickle_file,
                                          city_from=city_from,
                                          city_to=city_to,
                                          logger=logger)
        logger.info(f"Running API request for -> {outbound_date}")

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
        outbound_date_datetime = datetime.datetime.strptime(outbound_date, "%Y-%m-%d").date()
        next_outbound_date_datetime = outbound_date_datetime + datetime.timedelta(days=1)
        outbound_date = next_outbound_date_datetime.strftime("%Y-%m-%d")

        # pickle next date (process can resume from this point on the next run)
        pickle_data(file_name=pickle_file,
                    data_to_pickle={f"{city_from}-{city_to}": outbound_date},
                    logger=logger)

