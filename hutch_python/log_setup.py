"""
This module is used to set up and manipulate the ``logging`` configuration for
utilities like debug mode.
"""
import os
import time
import logging
import logging.config
from contextlib import contextmanager
from pathlib import Path

from .constants import FILE_YAML

import yaml

logger = logging.getLogger(__name__)


def setup_logging(dir_logs=None):
    """
    Sets up the ``logging`` configuration.

    Uses ``logging.yml`` to define the config
    and manages the ``log`` directory paths.

    Parameters
    ----------
    dir_logs: ``str`` or ``Path``, optional
        Path to the log directory. If omitted, we won't use a log file.
    """
    with open(FILE_YAML, 'rt') as f:
        config = yaml.safe_load(f.read())

    if dir_logs is None:
        # Remove debug file from the config
        del config['handlers']['debug']
        config['root']['handlers'].remove('debug')
    else:
        # Ensure Path object
        dir_logs = Path(dir_logs)

        # Subdirectory for year/month
        dir_month = dir_logs / time.strftime('%Y_%m')

        # Make the log directories if they don't exist
        # Make sure each level is all permissions
        for directory in (dir_logs, dir_month):
            if not directory.exists():
                directory.mkdir()
                directory.chmod(0o777)

        user = os.environ['USER']
        timestamp = time.strftime('%d_%Hh%Mm%Ss')
        log_file = '{}_{}.{}'.format(user, timestamp, 'log')
        path_log_file = dir_month / log_file
        path_log_file.touch()
        config['handlers']['debug']['filename'] = str(path_log_file)

    logging.config.dictConfig(config)
    # Disable parso logging because it spams DEBUG messages
    # https://github.com/ipython/ipython/issues/10946
    logging.getLogger('parso.python.diff').disabled = True
    logging.getLogger('parso.cache').disabled = True


def get_console_handler():
    """
    Helper function to find the console ``StreamHandler``.

    Returns
    -------
    console: ``StreamHandler``
        The ``Handler`` that prints to the screen.
    """
    root = logging.getLogger('')
    for handler in root.handlers:
        if handler.name == 'console':
            return handler
    raise RuntimeError('No console handler')


def get_console_level():
    """
    Helper function to get the console's log level.

    Returns
    -------
    level: ``int``
        Compare to ``logging.INFO``, ``logging.DEBUG``, etc. to see which log
        messages will be printed to the screen.
    """
    handler = get_console_handler()
    return handler.level


def set_console_level(level=logging.INFO):
    """
    Helper function to set the console's log level.

    Parameters
    ----------
    level: ``int``
        Likely one of ``logging.INFO``, ``logging.DEBUG``, etc.
    """
    handler = get_console_handler()
    handler.level = level


def debug_mode(debug=None):
    """
    Enable, disable, or check if we're in debug mode.

    Debug mode means that the console's logging level is ``logging.DEBUG`` or
    lower, which means we'll see all of the internal log messages that usually
    are not sent to the screen.

    Parameters
    ----------
    debug: ``bool``, optional
        If provided, we'll turn debug mode on (``True``) or off (``False``)

    Returns
    -------
    debug: ``bool`` or ``None``
        Returned if `debug_mode` is called with no arguments. This is ``True`
        if we're in debug mode, and ``False`` otherwise.
    """
    if debug is None:
        level = get_console_level()
        return level <= logging.DEBUG
    elif debug:
        set_console_level(level=logging.DEBUG)
    else:
        set_console_level(level=logging.INFO)


@contextmanager
def debug_context():
    """
    Context manager for running a block of code in `debug_mode`.

    For example:

    .. code-block:: python

        with debug_context():
            buggy_function()
    """
    old_level = get_console_level()
    debug_mode(True)
    yield
    set_console_level(level=old_level)


def debug_wrapper(f, *args, **kwargs):
    """
    Wrapper for running a function in `debug_mode`.

    Parameters
    ----------
    f: ``function``
        Wrapped function to call

    *args:
        Function arguments

    **kwargs:
        Function keyword arguments
    """
    with debug_context():
        f(*args, **kwargs)
