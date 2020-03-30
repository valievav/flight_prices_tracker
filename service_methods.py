import json
import logging
import os
import pickle
import sys
import time
import datetime
import send2trash
from bson import json_util  # to record JSON to file after mongodb


def timer(logger: logging.Logger, wait_time: int = 60) -> None:
    """
    Timer to count down certain number of seconds
    """
    stage_name = "TIMER"

    now = time.time()
    timer_time = now + wait_time
    while now <= timer_time:
        time.sleep(1)
        now += 1
    logger.debug(f"{stage_name} - Passed {wait_time} sec")


def retry(stage_name: str, current_try: int, max_tries: int, err: Exception or str, logger: logging.Logger)-> None:
    """
    Compares current run number with max run number and creates delay before the rerun.
    If max retries number is reached it exits the program.
    """

    if current_try <= max_tries:
        logger.error(f"{stage_name} - Try #{current_try} - Occurred error '{err}'. Rerunning after delay.")
        timer(logger=logger)
    else:
        logger.critical(f"{stage_name} - Try #{current_try}. Exiting the program.")
        sys.exit()  # no point in running further if no results in N tries


def get_outbound_date(outbound_date_config: str, pickle_file: str, city_from: str, city_to: str,
                      logger: logging.Logger)->str:
    """
    Returns outbound date either from pickled file (to continue process where left off) if pickled date > config date
    or from config if pickled date does not exist or it's < config date.
    Checks if outbound date is in the future (if it's in the past, program will be interrupted).
    """

    pickled_data = unpickle_data(file_name=pickle_file,
                                 logger=logger)
    outbound_date_pickled = pickled_data[f"{city_from}-{city_to}"]

    # use either date from config or from file (whichever is bigger if both exist)
    if outbound_date_pickled and outbound_date_pickled > outbound_date_config:
        outbound_date = outbound_date_pickled
        logging.debug(f"Date from file {outbound_date_pickled} > date from config {outbound_date_config}. "
                      f"Going to use date from file.")
    else:
        outbound_date = outbound_date_config
        logging.debug(f"Date from file {outbound_date_pickled} < date from config {outbound_date_config}. "
                      f"Going to use date from config.")

    # check date validity before run (interrupt if in the past)
    outbound_date_datetime = datetime.datetime.strptime(outbound_date, "%Y-%m-%d").date()
    if datetime.datetime.now().date() > outbound_date_datetime:
        sys.exit(f"Outbound date {outbound_date_datetime} is in the past. Please fix.")

    return outbound_date


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


def files_cleaner(path_to_clean: str, extension: str, logger: logging.Logger,
                  exception_file: str = None, to_keep_number: int = 5) -> None:
    """
    Cleans up old files and keeps the passed number of files only
    """

    stage_name = 'CLEANUP_FILES'
    os.chdir(path_to_clean)

    # find all files
    files = [file for file in os.listdir('.') if file.endswith(extension) and file != exception_file]
    logger.debug(f"{stage_name} - Found {len(files)} {extension} files")

    if len(files) <= to_keep_number:  # do nothing if low number of files
        logger.debug(f"{stage_name} - No {extension} files to delete")
        return None

    # get created date for files
    files_with_dates = []
    for file in files:
        epoch_date = os.path.getctime(os.path.join(os.getcwd(), file))
        str_date = datetime.datetime.fromtimestamp(epoch_date).strftime('%Y-%m-%d %H:%M:%S')
        files_with_dates.append([file, str_date])

    sorted_files_with_dates = sorted(files_with_dates, key=lambda elem: elem[1], reverse=True)

    # create to_keep list with file names only
    files_to_keep = [file_data[0] for file_data in sorted_files_with_dates[0:to_keep_number]]
    del sorted_files_with_dates[0:to_keep_number]
    logger.debug(f"{stage_name} - Remained {len(files_to_keep)} {extension} files  - {files_to_keep}")

    # create to_delete list with file names only
    files_to_delete = [file_data[0] for file_data in sorted_files_with_dates]
    del sorted_files_with_dates
    for file in files_to_delete:
        send2trash.send2trash(os.path.join(path_to_clean, file))
    logger.debug(f"{stage_name} - Deleted {len(files_to_delete)} {extension} files - {files_to_delete}")
