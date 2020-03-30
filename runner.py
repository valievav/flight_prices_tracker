"""
Gets Live API results, records them into MongoDB, records into file and finds min price.
"""

import os
from config import *
from logger import create_logger
from get_api_results_for_n_days import get_api_results_for_n_days
from mongodb_methods import connect_to_mongodb, find_flights_under_threshold_price
from service_methods import files_cleaner


def main():

    # create logger
    cwd = os.getcwd()
    log_file_folder_path = os.path.join(cwd, log_files_folder)
    logger = create_logger(log_file_folder_path=log_file_folder_path,
                           log_file_name=log_file)

    # connect to db
    collection = connect_to_mongodb(mongodb_instance=instance,
                                    mongodb=db,
                                    mongodb_collection=db_collection,
                                    logger=logger)

    # get LIVE API results, record values to db
    get_api_results_for_n_days(days=days_to_request,
                               pickle_file=pickle_file,
                               base_url=base_url,
                               headers=headers,
                               cabin_class=cabin_class,
                               country=country,
                               currency=currency,
                               locale_lang=locale_lang,
                               city_from=city_from,
                               city_to=city_to,
                               country_from=country_from,
                               country_to=country_to,
                               outbound_date=outbound_date,
                               adults_count=adults_count,
                               max_retries=max_retries,
                               json_files_folder=json_files_folder,
                               json_file=json_file,
                               collection=collection,
                               logger=logger,
                               save_to_file=save_to_file,
                               live_api_mode=live_api_mode)

    # find flights with price < threshold
    find_flights_under_threshold_price(threshold=price_threshold,
                                       search_date=outbound_date,
                                       collection=collection,
                                       logger=logger)

    # clean up log files
    log_path_to_clean = os.path.join(cwd, log_files_folder)
    files_cleaner(path_to_clean=log_path_to_clean,
                  extension='log',
                  to_keep_number=log_files_to_keep,
                  logger=logger)


if __name__ == "__main__":
    main()

