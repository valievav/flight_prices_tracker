import time
import logging
import sys


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

