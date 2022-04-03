import asyncio
import logging
import time


def resolve_log_level(level: str) -> int:
    """Resolve the logging level from a string

    This method will try to get the actual logging level from the logging package

    If no valid logging level is supplied this method will return the info level

    :param level: The name of the level which should be resolved
    :return: The logging level which may be used in the configuration of loggers
    """
    return getattr(logging, level.upper(), logging.INFO)


async def is_host_available(host: str, port: int, timeout: int = 10) -> bool:
    """Check if the specified host is reachable on the specified port

    :param host: The hostname or ip address which shall be checked
    :param port: The port which shall be checked
    :param timeout: Max. duration of the check
    :return: A boolean indicating the status
    """
    _end_time = time.time() + timeout
    while time.time() < _end_time:
        try:
            # Try to open a connection to the specified host and port and wait a maximum time of five seconds
            _s_reader, _s_writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5
            )
            # Close the stream writer again
            _s_writer.close()
            # Wait until the writer is closed
            await _s_writer.wait_closed()
            return True
        except:
            # Since the connection could not be opened wait 5 seconds before trying again
            await asyncio.sleep(5)
    return False
