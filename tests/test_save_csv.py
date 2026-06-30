import os
import tempfile

from save_csv import write_csv


def test_write_csv_creates_expected_file():
    # Sample data
    test_data = [
        [1, "http://example.com/image1.jpg", "Nice item", "new", "10", "KY - 10/11/2023", "http://example.com/item1"],
        [2, "http://example.com/image2.jpg", "Used item", "used", "5", "OD - 2/8/2024", "http://example.com/item2"]
    ]

    expected_header = ['id', 'image_link', 'describe', 'state_tag', 'price', 'location_date', 'describe_link']

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='r+', delete=False, newline='', suffix='.csv') as tmp_file:
        file_name = tmp_file.name

    try:
        # Run the function
        write_csv(file_name, test_data)

        # Read back and verify content
        with open(file_name, newline='', encoding='utf-8') as f:
            reader = list(csv.reader(f))
            assert reader[0] == expected_header
            assert reader[1:] == [[str(cell) for cell in row] for row in test_data]
    finally:
        os.remove(file_name)  # Clean up the file
