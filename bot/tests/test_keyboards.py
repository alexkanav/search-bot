import pytest
from aiogram.types import ReplyKeyboardMarkup

from keyboards import make_multiline_keyboard, make_row_keyboard


def test_make_row_keyboard__valid_items__creates_single_row_keyboard():
    items = ["Search", "Cancel"]

    keyboard = make_row_keyboard(items)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert keyboard.resize_keyboard is True
    assert [
               [button.text for button in row]
               for row in keyboard.keyboard
           ] == [items]


def test_make_row_keyboard__empty_items__creates_empty_row():
    keyboard = make_row_keyboard([])

    assert keyboard.keyboard == [[]]


def test_make_multiline_keyboard__items_fit_one_row__creates_one_row():
    items = ["A", "B", "C"]

    keyboard = make_multiline_keyboard(items, 3)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert keyboard.resize_keyboard is True
    assert [
               [button.text for button in row]
               for row in keyboard.keyboard
           ] == [items]


def test_make_multiline_keyboard__items_exceed_row_size__splits_rows():
    items = ["A", "B", "C", "D", "E"]

    keyboard = make_multiline_keyboard(items, 2)

    assert [
               [button.text for button in row]
               for row in keyboard.keyboard
           ] == [
               ["A", "B"],
               ["C", "D"],
               ["E"],
           ]


def test_make_multiline_keyboard__empty_items__creates_empty_keyboard():
    keyboard = make_multiline_keyboard([], 2)

    assert isinstance(keyboard, ReplyKeyboardMarkup)
    assert keyboard.keyboard == []


@pytest.mark.parametrize("buttons_per_row", [0, -1, -5])
def test_make_multiline_keyboard__invalid_row_size__raises_value_error(
        buttons_per_row,
):
    with pytest.raises(ValueError, match="buttons_per_row"):
        make_multiline_keyboard(["A"], buttons_per_row)
