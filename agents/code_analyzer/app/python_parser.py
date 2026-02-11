import ast 
from schema import FunctionSchema, FileSchema


EXTERNAL_IO_CALLS = {"open", "requests", "httpx", "aiohttp"}


class FunctionAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.has_try_except = False
        self.has_entry_log = False
        self.has_error_log = False
        self.calls_external_io = False

    def visit_Try(self, node):
        self.has_try_except = True
        self.generic_visit(node)


    def visit_Call(self, node):
        # logging.xxx(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in {"info", "debug"}:
                self.has_entry_log = True
            if node.func.attr in {"error", "exception", "critical"}:
                self.has_error_log = True

        # open(), requests.get(), etc
        if isinstance(node.func, ast.Name):
            if node.func.id == "open":
                self.calls_external_io = True

        self.generic_visit(node)


def parse_python_file(file_path: str) -> FileSchema:
    with open(file_path, "r") as f:
        tree = ast.parse(f.read())

    functions = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            analyzer = FunctionAnalyzer()
            analyzer.visit(node)

            functions.append(
                FunctionSchema(
                    function_name=node.name,
                    has_entry_log=analyzer.has_entry_log,
                    has_error_log=analyzer.has_error_log,
                    has_try_except=analyzer.has_try_except,
                    calls_external_io=analyzer.calls_external_io,
                )
            )

    return FileSchema(
        file_name=file_path,
        functions=functions
    )