from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from telegram.keyboards import make_row_keyboard, make_multiline_keyboard


def test_make_row_keyboard__valid_items__creates_single_row_keyboard():
    items = ["Yes", "No"]
    keyboard = make_row_keyboard(items)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert len(keyboard.keyboard) == 1
    assert [button.text for button in keyboard.keyboard[0]] == items
    assert keyboard.resize_keyboard is True


def test_make_multiline_keyboard__even_number_of_items__creates_multiple_full_rows():
    items = ["A", "B", "C", "D"]
    keyboard = make_multiline_keyboard(items, buttons_per_row=2)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert keyboard.resize_keyboard is True
    flat_buttons = [btn for row in keyboard.keyboard for btn in row]
    assert len(flat_buttons) == len(items)
    assert all(isinstance(btn, KeyboardButton) for btn in flat_buttons)

    assert len(keyboard.keyboard) == 2

    assert [button.text for button in keyboard.keyboard[0]] == ["A", "B"]
    assert [button.text for button in keyboard.keyboard[1]] == ["C", "D"]


def test_make_multiline_keyboard__odd_number_of_items__places_remaining_button_in_last_row():
    items = ["A", "B", "C"]

    keyboard = make_multiline_keyboard(items, buttons_per_row=2)

    assert [button.text for button in keyboard.keyboard[0]] == ["A", "B"]
    assert [button.text for button in keyboard.keyboard[1]] == ["C"]
