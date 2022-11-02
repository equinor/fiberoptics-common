class SemanticVersion(tuple):
    """Parses a (semantic) version number given by `major.minor.patch`.

    Semantic versioning is a standard defined by https://semver.org/ with the following
    increments:

    major
        When you make breaking changes
    minor
        When you add functionality in a backwards compatible manner
    patch
        When you make backwards compatible changes

    """

    major: int
    minor: int
    patch: int

    def __new__(cls, major, minor=0, patch=0):
        if isinstance(major, str):
            # Split `major` assuming it is formatted as "1.2.3"
            major = major.split(".")

        if not isinstance(major, int):
            # Unpack `major` assuming it is an iterable such as (1,2,3)
            major, minor, patch = major

        # Convert to integers, raising TypeError if it fails
        major, minor, patch = int(major), int(minor), int(patch)

        return super().__new__(cls, (major, minor, patch))

    def __init__(self, major, minor=0, patch=0):
        super().__init__()
        # Ignore input and use the already parsed `self`
        self.major, self.minor, self.patch = self

    def __repr__(self) -> str:
        return f"{type(self).__name__}(major={self.major}, minor={self.minor}, patch={self.patch})"
