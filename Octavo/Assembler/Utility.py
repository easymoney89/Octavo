#! /usr/bin/python3

from bitstring import BitArray


class Utility:
    """Common utility functions for all other classes."""

    def __init__ (self):
        pass

    def try_int (self, value):
        """Wrapper around int() to deal with non-numeric strings and provide debug info."""
        if value is None:
            return None
        if type(value) == int:
            return value
        if type(value) == BitArray:
            return value
        try:
            value = int(value, 0)
        except ValueError:
            # Assume it's a label string. Leave it alone and pass it back out for later resolution.
            pass
        except TypeError:
            print("\nInvalid type for int() conversion. Input {0} of type {1}.\n".format(value, type(value)))
            raise TypeError
        return value

