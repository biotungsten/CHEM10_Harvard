def pytest_configure(config):
    config.addinivalue_line("markers", "environment: marks tests that verify the environment setup")
    config.addinivalue_line("markers", "physical: marks tests that need a physical setup")
