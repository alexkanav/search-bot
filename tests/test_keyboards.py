from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

from aiogram_source.keyboards import make_row_keyboard, make_multiline_keyboard, make_row_inline_keyboard


def test_make_row_keyboard():
    items = ['Yes', 'No']
    keyboard = make_row_keyboard(items)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert keyboard.keyboard[0][0].text == 'Yes'
    assert keyboard.keyboard[0][1].text == 'No'
    assert keyboard.resize_keyboard is True


def test_make_multiline_keyboard():
    items = ['A', 'B', 'C', 'D']
    number_of_lines = 2
    keyboard = make_multiline_keyboard(items, number_of_lines)

    # Check type and number of buttons
    assert isinstance(keyboard, ReplyKeyboardMarkup)
    flat_buttons = [btn for row in keyboard.keyboard for btn in row]
    assert len(flat_buttons) == len(items)
    assert all(isinstance(btn, KeyboardButton) for btn in flat_buttons)

    # Optional: Check row distribution if you want stricter validation
    assert len(keyboard.keyboard) == 2  # 2 lines expected


def test_make_row_inline_keyboard_with_urls_and_callbacks():
    items = [
        {"Google": {"url": "https://google.com"}},
        {"Click me": {"callback_data": "clicked"}},
    ]
    keyboard = make_row_inline_keyboard(items)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 2

    first_button = keyboard.inline_keyboard[0][0]
    assert isinstance(first_button, InlineKeyboardButton)
    assert first_button.text == "Google"
    assert first_button.url == "https://google.com"

    second_button = keyboard.inline_keyboard[1][0]
    assert isinstance(second_button, InlineKeyboardButton)
    assert second_button.text == "Click me"
    assert second_button.callback_data == "clicked"
