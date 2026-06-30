import pytest
from unittest.mock import patch, MagicMock

from selenium_scraping import run_driver, URL

@pytest.mark.parametrize("browser", ["chrome", "edge", "firefox"])
@patch("selenium_scraping.webdriver.Chrome")
@patch("selenium_scraping.webdriver.Edge")
@patch("selenium_scraping.webdriver.Firefox")
def test_run_driver_mocks(mock_firefox, mock_edge, mock_chrome, browser):
    """
    Test the run_driver function by mocking the browser initialization.
    The test ensures that the correct WebDriver is returned and used properly.
    """

    # Create a mock driver
    mock_driver = MagicMock()

    # Return the mock driver based on the browser being tested
    if browser == "chrome":
        mock_chrome.return_value = mock_driver
    elif browser == "edge":
        mock_edge.return_value = mock_driver
    elif browser == "firefox":
        mock_firefox.return_value = mock_driver

    # Call the run_driver function
    driver = run_driver(browser)

    # Ensure the returned driver is the mock driver
    assert driver == mock_driver

    # Check if 'get' method was called with the correct URL
    mock_driver.get.assert_called_once_with(URL)

    # Check if 'implicitly_wait' method was called with 20 seconds
    mock_driver.implicitly_wait.assert_called_once_with(20)


@pytest.mark.parametrize("browser", ["chrome", "firefox", "edge"])
def test_run_driver_real_browser(browser):
    """
    Test that the browser launches correctly and navigates to the correct URL.
    This test will run on multiple browsers (chrome, firefox, edge) for cross-browser compatibility.
    """

    # Initialize the driver
    driver = run_driver(browser)

    try:
        # Assert that the driver is initialized correctly
        assert driver is not None, f"Driver for {browser} did not initialize correctly."

        # Wait for the page to load and check if the URL is as expected
        driver.implicitly_wait(10)  # Wait up to 10 seconds for the page to load
        assert URL in driver.current_url, f"Expected URL '{URL}', but got '{driver.current_url}'"

        # Optionally check if the page has a title (this can be another check to confirm loading)
        assert driver.title != "", f"Page title is empty for {browser}."

    finally:
        # Ensure the driver quits even if the test fails
        driver.quit()
