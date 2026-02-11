from schema import FileSchema


def find_risky_functions(file_data: FileSchema):
    """
    Rule:
    External IO + no try/except = risky
    """
    risky = []

    for fn in file_data.functions:
        if fn.calls_external_io and not fn.has_try_except:
            risky.append(fn.function_name)

    return risky


def find_missing_logs(file_data: FileSchema):
    """
    Rule:
    No entry log + no error log = bad observability
    """
    bad = []

    for fn in file_data.functions:
        if not fn.has_entry_log and not fn.has_error_log:
            bad.append(fn.function_name)

    return bad
