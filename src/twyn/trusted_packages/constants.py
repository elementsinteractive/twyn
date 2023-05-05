from typing import NewType

Url = NewType("Url", str)

TOP_PYPI_PACKAGES = Url(
    "https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.min.json"
)


ADJACENCY_MATRIX = {
    "1": ["2", "q", "w"],
    "2": ["1", "3", "q", "w"],
    "3": ["2", "4", "w", "e"],
    "4": ["3", "5", "e", "r"],
    "5": ["4", "6", "r", "t"],
    "6": ["5", "7", "t", "y"],
    "7": ["6", "8", "y", "u"],
    "8": ["7", "9", "u", "i"],
    "9": ["8", "0", "i", "o"],
    "0": ["9", "o", "p"],
    "q": ["1", "2", "w", "a"],
    "w": ["2", "3", "q", "e", "a", "s", "d"],
    "e": ["3", "4", "w", "r", "s", "d", "f"],
    "r": ["4", "5", "e", "t", "d", "f", "g"],
    "t": ["5", "6", "r", "y", "f", "g", "h"],
    "y": ["6", "7", "t", "u", "g", "h", "j"],
    "u": ["7", "8", "y", "i", "h", "j", "k"],
    "i": ["8", "9", "u", "o", "j", "k", "l"],
    "o": ["9", "0", "i", "p", "k", "l"],
    "p": ["0", "o", "l"],
    "a": ["q", "w", "s", "z"],
    "s": ["q", "w", "e", "a", "d", "z", "x"],
    "d": ["w", "e", "r", "s", "f", "x", "c"],
    "f": ["e", "r", "t", "d", "g", "c", "v"],
    "g": ["r", "t", "y", "f", "h", "v", "b"],
    "h": ["t", "y", "u", "g", "j", "b", "n"],
    "j": ["y", "u", "i", "h", "k", "n", "m"],
    "k": ["u", "i", "o", "j", "l", "m"],
    "l": ["i", "o", "p", "k"],
    "z": ["a", "s", "x"],
    "x": ["s", "d", "z", "c"],
    "c": ["d", "f", "x", "v"],
    "v": ["f", "g", "c", "b"],
    "b": ["g", "h", "v", "n"],
    "n": ["h", "j", "b", "m"],
    "m": ["j", "k", "n"],
}
