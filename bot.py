import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from chatgpt import openai_request
from dotenv import load_dotenv


# Initialize bot and dispatcher
load_dotenv()
bot = Bot(token=os.environ.get('API_TOKEN'))
dp = Dispatcher(bot, storage=MemoryStorage())


# Enable logging
logging.basicConfig(level=logging.INFO)


# Command handler to start the interaction
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    """Handles the /start command."""
    try:
        # Create a custom keyboard with a button
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        button = KeyboardButton("Локації")
        keyboard.add(button)
        await message.reply("Привіт! Почнемо працювати.", reply_markup=keyboard)
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in start command handler: {e}")


# Handler to respond to the button click
@dp.message_handler(lambda message: message.text == "Локації")
async def show_options(message: types.Message):
    """Handles the location select"""
    try:
        # Create an inline keyboard with 5 options
        options = ["Локація 1", "Локація 2", "Локація 3", "Локація 4", "Локація 5"]
        keyboard = types.InlineKeyboardMarkup()
        for option_text in options:
            callback_button = types.InlineKeyboardButton(text=option_text, callback_data=option_text)
            keyboard.add(callback_button)
        await bot.send_message(message.chat.id, "Ось локації:", reply_markup=keyboard)
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in show_options handler: {e}")


@dp.callback_query_handler(lambda c: c.data.startswith("Локація"))
async def process_initial_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handles the callback query for initial location selection."""
    try:
        option = callback_query.data  # Extract the selected option
        # Create an inline keyboard with 5 additional options
        additional_options = [f"Пункт {i}" for i in range(1, 4)]
        additional_options.append(f'Все чисто')
        additional_options.append(f'Залишити коментар')
        additional_keyboard = InlineKeyboardMarkup()
        for additional_option_text in additional_options:
            callback_button = InlineKeyboardButton(text=additional_option_text,
                                                   callback_data=additional_option_text)
            additional_keyboard.add(callback_button)
        await state.update_data(location=option)
        # Send the additional options
        await bot.send_message(callback_query.from_user.id, f"Чек-лист для {option}:",
                               reply_markup=additional_keyboard)
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in process_initial_callback handler: {e}")


# Callback query handler for the first 4 additional options
@dp.callback_query_handler(lambda c: c.data.startswith("Пункт") or c.data.startswith("Все чисто")
                           and not c.data.endswith("Залишити коментар"), state="*")
async def process_additional_option_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handles the callback query for the first 4 additional options."""
    try:
        # Extract the selected additional option
        additional_option = callback_query.data
        # Write the additional option directly into the user's state
        await state.update_data(check_list=additional_option)
        user_state = await state.get_data()
        # Send a confirmation message
        await bot.send_message(callback_query.from_user.id,
                               f"Your choices: Location - {user_state.get('location')}; "
                               f"Check-list - {user_state.get('check_list')}")
        gpt = openai_request(user_state)
        await bot.send_message(callback_query.from_user.id, gpt)
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in process_additional_option_callback handler: {e}")


# Inline query handler for additional options
@dp.callback_query_handler(lambda c: c.data.endswith("Залишити коментар"))
async def process_leave_comment_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Handles the callback query for the option "Залишити коментар"."""
    try:
        # Prompt the user to leave a comment
        option = callback_query.data
        await state.update_data(check_list=option)
        await bot.send_message(callback_query.from_user.id, "Введіть коментар:")
        # Set the user's state to 'waiting_for_comment'
        await state.set_state("waiting_for_comment")
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in process_leave_comment_callback handler: {e}")


# Message handler for collecting comments
@dp.message_handler(state="waiting_for_comment")
async def process_comment(message: types.Message, state: FSMContext):
    """Handle the message for collecting comments during the 'waiting_for_comment' state."""
    try:
        # Process the comment
        comment = message.text
        await state.update_data(comment=comment)
        # Ask the user if they want to add a photo with buttons
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text='Yes', callback_data='photo_yes'))
        keyboard.add(InlineKeyboardButton(text='No', callback_data='photo_no'))
        await bot.send_message(message.chat.id, "Do you want to add a photo with your comment?",
                               reply_markup=keyboard)
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in process_comment handler: {e}")


# Message handler for collecting photos
@dp.callback_query_handler(lambda c: c.data in ['photo_yes', 'photo_no'], state="*")
async def process_photo(callback_query: types.CallbackQuery, state: FSMContext):
    """Handles the callback query for collecting photos."""
    try:
        # Retrieve the user's state
        user_state = await state.get_data()
        if callback_query.data == 'photo_yes':
            await bot.send_message(callback_query.from_user.id, "Waiting for a photo")
        else:
            await bot.send_message(callback_query.from_user.id,
                                   f"Your choices: Location - {user_state.get('location')}; "
                                   f"Check-list - {user_state.get('check_list')}; "
                                   f"Comment - {user_state.get('comment')}")
            gpt = openai_request(user_state)
            await bot.send_message(callback_query.from_user.id, gpt)
            await state.finish()
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in process_photo handler: {e}")


@dp.message_handler(state="*", content_types=types.ContentType.PHOTO)
async def process_photo(message: types.Message, state: FSMContext):
    """Handles the message with a photo and update the user's state accordingly."""
    try:
        user_state = await state.get_data()
        if message.photo:
            # Assuming you want to use the first (and only) photo in the list
            photo = message.photo[-1]
            photo_file_id = photo.file_id

            # Save the photo file to a location (you can customize this based on your needs)
            photo_file = await bot.get_file(photo_file_id)
            photo_link = photo_file.file_path

            # Optionally, you can store the photo_link in the user's state or perform any other processing
            await state.update_data(photo_link=photo_link)
            await bot.send_message(message.chat.id, f"Your choices: Location - {user_state.get('location')}; "
                                                    f"Check-list - {user_state.get('check_list')}; "
                                                    f"Comment - {user_state.get('comment')}; "
                                                    f"Photo-link - {photo_link}")
            gpt = openai_request(user_state)
            await bot.send_message(message.chat.id, gpt)
            # Reset the state to the initial state
            await state.finish()
        else:
            keyboard = InlineKeyboardMarkup()

            keyboard.add(InlineKeyboardButton(text='Yes', callback_data='photo_yes'))
            keyboard.add(InlineKeyboardButton(text='No', callback_data='photo_no'))

            await bot.send_message(message.chat.id, "Do you want to add a photo with your comment?",
                                   reply_markup=keyboard)
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in process_photo handler: {e}")


@dp.message_handler(commands=['cancel'], state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    """Handles the /cancel command to cancel the ongoing operation and clear the user's state."""
    try:
        # Clear the state and send a message
        await state.finish()
        await bot.send_message(message.chat.id, "Operation canceled. State cleared.")
    except Exception as e:
        # Handle any unexpected errors and log them
        print(f"Error in cancel_handler: {e}")


# Start the bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
