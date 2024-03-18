import os
import time
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.testclient import TestClient

from safe_init import tracer
from safe_init.tracer import FunctionCall, FunctionCallSummary
from safe_init.utils import aggregate_traced_fn_calls, format_traces

MS_IN_NS = 1_000_000


class TestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        content_type = request.headers.get("Content-Type")
        if content_type == "image/jpeg":
            from starlette.responses import Response

            return Response("Unsupported Media Type", status_code=415)

        response = await call_next(request)
        return response


class TestTracer(unittest.TestCase):
    RESPONSE = {"message": "Hello World"}

    def get_fastapi_response(self):
        app = FastAPI()

        app.add_middleware(TestMiddleware)

        @app.get("/")
        def root():
            from safe_init.safe_logging import get_logger

            logger = get_logger()

            def do_something():
                logger.info("I'm about to fall asleep")
                import time

                time.sleep(0.05)
                logger.info("What a nice nap I had!")

            do_something()
            return self.RESPONSE

        client = TestClient(app)

        return client.get("/")

    def test_tracing_time(self):
        untraced_fn = self.get_fastapi_response
        traced_fn = tracer.traced(untraced_fn)

        # Call untraced fn once to make sure we execute both tracked calls with the same app state
        untraced_fn()

        untraced_t0 = time.time_ns()
        untraced_response = untraced_fn()
        untraced_t1 = time.time_ns()

        assert untraced_response.status_code == 200
        assert untraced_response.json() == self.RESPONSE

        traced_t0 = time.time_ns()
        traced_response = traced_fn()
        traced_t1 = time.time_ns()

        assert traced_response.status_code == 200
        assert traced_response.json() == self.RESPONSE

        untraced_time_ns = untraced_t1 - untraced_t0
        traced_time_ns = traced_t1 - traced_t0
        time_delta_ns = traced_time_ns - untraced_time_ns

        # Assert that traced execution isn't more than 10 ms longer than the classic one.
        # If it is, we're probably doing too much in the on_frame function.
        assert time_delta_ns < 10 * MS_IN_NS

    def test_traces(self):
        fn = tracer.traced(self.get_fastapi_response)
        response = fn()
        assert response.status_code == 200
        assert response.json() == self.RESPONSE
        assert tracer.is_traced()
        calls = tracer.get_function_calls()
        assert len(calls) > 0
        called_fns = {call.function_name for call in calls}
        assert any("get_fastapi_response" in fn for fn in called_fns)
        assert any("TestTracer" in fn for fn in called_fns)
        assert "Starlette.add_middleware" in called_fns
        assert "Starlette.add_route" in called_fns
        assert "TestClient.__init__" in called_fns

    def test_aggregation(self):
        traces = [
            FunctionCall("foo", 10.1, "file1.py"),
            FunctionCall("foo", 5.1, "file1.py"),
            FunctionCall("bar", 3.1, "file2.py"),
            FunctionCall("bar", 2.1, "file2.py"),
            FunctionCall("baz", 1.1, "file3.py"),
        ]
        aggregated = aggregate_traced_fn_calls(traces)
        assert len(aggregated) == 3
        assert aggregated == [
            FunctionCallSummary("foo", 2, 15.2, "file1.py"),
            FunctionCallSummary("bar", 2, 5.2, "file2.py"),
            FunctionCallSummary("baz", 1, 1.1, "file3.py"),
        ]

    @patch.dict(os.environ, {"SAFE_INIT_TRACER_HOME_PATHS": "/var/task"})
    def test_formatting(self):
        calls = [
            FunctionCallSummary("foo", 2, 15.2, "/var/task/lambdas/file1.py"),
            FunctionCallSummary("bar", 2, 5.2, "/var/lib/some-library/file2.py"),
            FunctionCallSummary("baz", 1, 1.1, "file3.py"),
            FunctionCallSummary("qux", 1, 0.1, "file4.py"),
        ]
        formatted = format_traces(calls, 3)
        expected = (
            "🕵️ *Top 3 most time-consuming function calls:*\n"
            "1. `foo`: *15.200s*, called 2 times (`/var/task/lambdas/file1.py`) :zap:\n"
            "2. `bar`: *5.200s*, called 2 times (`/var/lib/some-library/file2.py`) \n"
            "3. `baz`: *1.100s*, called 1 time (`file3.py`) "
        )

        assert formatted == expected
