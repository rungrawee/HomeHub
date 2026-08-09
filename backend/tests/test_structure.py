import unittest

from app.main import create_app


class BackendStructureTests(unittest.TestCase):
    def test_app_has_health_endpoint(self):
        app = create_app()
        routes = {route.path for route in app.routes}
        self.assertIn("/health", routes)


if __name__ == "__main__":
    unittest.main()
