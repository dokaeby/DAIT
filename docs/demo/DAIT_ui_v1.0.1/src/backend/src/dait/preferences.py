"""이전 경로 호환 모듈."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("dait.services.preference_service")
