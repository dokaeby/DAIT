"""호환 경로: 실제 구현은 dait.repositories.user_repository에 있습니다."""
import importlib
import sys

if __name__ == "__main__":
    import runpy
    runpy.run_module("dait.repositories.user_repository", run_name="__main__")
else:
    sys.modules[__name__] = importlib.import_module("dait.repositories.user_repository")
