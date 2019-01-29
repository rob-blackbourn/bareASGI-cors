"""Header utilities

Headers are represented as a list of tuples of two bytes; the first being the name, and the second the value.

The AGSI spec requires the header names to be lower case. The order of the headers need not be preserved by the server,
but the order of the values must be.
"""

import collections
from typing import Optional, MutableMapping, List, Any
from bareasgi.types import Header


def find_headers(headers: List[Header], name: bytes) -> List[Header]:
    """Find all headers matching the given tag

    :param headers: A list of headers represented as a tuple of two bytes: this first being the name, the second being
        the value.
    :param name: The name of the headers to find.
    :return: A list of matching headers.
    """
    return [(k, v) for k, v in headers if k == name]


def find_header_value(headers: List[Header], name: bytes) -> Optional[Any]:
    """Finds the value for a given header.

    :param headers: A list of headers represented as a tuple of two bytes: this first being the name, the second being
        the value.
    :param name: The name of the header to find.
    :return: The value of the matched header or None.
    :raise: A KeyError is raised if more than one header was matched.

    """
    matches = find_headers(headers, name)
    if len(matches) > 1:
        raise KeyError(f'multiple matches for {name}')
    elif len(matches) == 1:
        return matches[0][1]
    else:
        return None


def headers_to_dict(headers: List[Header]) -> MutableMapping[bytes, List[bytes]]:
    """Convert a list of headers into a dictionary where the key is the header name and the value is a list of the
    values of the headers for that name

    :param headers: A list of headers.
    :return: A dictionary where the key is the header name and the value is a list of the values of the headers for that
        name
    """
    items: MutableMapping[bytes, List[bytes]] = collections.defaultdict(list)
    for name, value in headers:
        items[name].append(value)
    return items


def upsert_header(headers: List[Header], name: bytes, value: bytes):
    for i in range(len(headers)):
        if headers[i][0] == name:
            headers[i] = (name, value)
            return
    headers.append((name, value))
