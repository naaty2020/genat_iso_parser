class LengthError(Exception):
    def __init__(self, errors, message='Invalid Field Length.'):
        super().__init__(message)
        self.errors = errors

class InvalidBitmap(Exception):
    def __init__(self, errors, message='Invalid Bitmap.'):
        super().__init__(message)
        self.errors = errors

class PadValueError(ValueError):
    def __init__(self, errors, message='Non Integer Field Length.'):
        super().__init__(message)
        self.errors = errors

class UnsupportedIsoVersion(KeyError):
    def __init__(self, errors):
        message = f'Unsupported Iso version {errors["version"]}.'
        super().__init__(message)
        self.errors = errors

class FieldNumberError(Exception):
    def __init__(self, errors, message='Invalid Field Number.'):
        super().__init__(message)
        self.errors = errors