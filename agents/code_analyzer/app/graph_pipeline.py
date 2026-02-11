from python_parser import parse_python_file
from analysis_tools import find_risky_functions, find_missing_logs


def run_pipeline(file_path:str):
    #node 1: parse
    file_data = parse_python_file(file_path=file_path)

    #node 2: analyse
    risky = find_risky_functions(file_data=file_data)
    missing_logs = find_missing_logs(file_data=file_data)

    #node 3 : aggregate

    output = {
        "file_name": file_data.file_name,
        "risky_functions": risky,
        "missing_logs": missing_logs
    }

    return output
