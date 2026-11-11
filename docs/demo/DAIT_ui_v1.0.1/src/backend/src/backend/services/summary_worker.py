"""호환 경로: 실제 구현은 dait.services.summary_worker에 있습니다."""
import importlib
import sys

if __name__ == "__main__":
    import runpy
    runpy.run_module("dait.services.summary_worker", run_name="__main__")
else:
    sys.modules[__name__] = importlib.import_module("dait.services.summary_worker")
