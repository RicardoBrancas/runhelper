import atexit
import logging
import signal
import time
from typing import Any, Union, Optional, Callable

logger = logging.getLogger()

tags = {}
tags_helper = {}
at_exit_tags = set()
sigterm_callback: Optional[Callable] = None


def init_logger(logger_name: str):
    """Initialize a logging.Logger instance based on the given name"""
    global logger
    logger = logging.getLogger(logger_name)


def register_sigterm_handler(callback: Optional[Callable] = None):
    """Register a SIGTERM signal handler that will log tags that have been set as at_exit tags.
       Optionally receives a callback that will also be called during the SIGTERM event."""
    global sigterm_callback
    sigterm_callback = callback
    signal.signal(signal.SIGTERM, termination_handler)


def log_any(tag: str, value: Any):
    """Log an arbitrary value for the given tag"""
    logger.info(f'runhelper.{tag}=%s', str(value))


def log_tag(tag: str):
    """Log the current stored value for the given tag"""
    if tag not in tags:
        raise ValueError(f"Unknown tag '{tag}'")
    log_any(tag, tags[tag])


def create_tag(tag: str, at_exit_print: bool = True):
    """Create a new tag with the given name, optionally registering it as an at_exit tag.
       At exit tags will be printed when the program terminates (see register_sigterm_handler())."""
    if tag in tags:
        raise ValueError(f"Tried to create duplicate tag '{tag}'")
    if at_exit_print:
        at_exit_tags.add(tag)
    tags[tag] = None


def create_int_tag(tag: str, at_exit_print: bool = True):
    """Create a new integer tag with the given name, optionally registering it as an at_exit tag.
           At exit tags will be printed when the program terminates (see register_sigterm_handler())."""
    create_tag(tag, at_exit_print)
    tags[tag] = 0


def create_float_tag(tag: str, at_exit_print: bool = True):
    """Create a new float tag with the given name, optionally registering it as an at_exit tag.
           At exit tags will be printed when the program terminates (see register_sigterm_handler())."""
    create_tag(tag, at_exit_print)
    tags[tag] = 0.0


def timer_start(tag: str):
    """Start a timer for the given tag.
       If the tag does not exist, create a new float tag with that name."""
    if tag not in tags:
        create_float_tag(tag)
    tags_helper[tag] = time.perf_counter_ns()


def timer_stop(tag: str):
    """Stop the currently running timer for the given tag. The timer should have been started before calling this function.
       When the timer is stopped, the time is accumulated in the tag store, as a floating point number representing the total number of seconds elapsed."""
    if tag not in tags_helper:
        raise ValueError(f"Timer not previously started for tag '{tag}'")
    tags[tag] += float(time.perf_counter_ns() - tags_helper[tag]) / 1e9


def tag_increment(tag: str, value: Union[int, float] = 1):
    """Increment the given tag by an arbitrary number (by default 1).
       If the tag does not exist, create a new integer tag with that name."""
    if tag not in tags:
        create_int_tag(tag)
    tags[tag] += value


@atexit.register
def log_at_exit():
    for tag in at_exit_tags:
        log_tag(tag)


def termination_handler(signum=None, frame=None):
    logger.warning('Termination signal received. Exiting...')
    log_at_exit()
    if sigterm_callback:
        sigterm_callback()
    exit()
