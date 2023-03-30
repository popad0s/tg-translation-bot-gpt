import logging
import io
import requests
import textwrap
import constants as consts
import pytesseract
import googletrans

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #  
from PIL import Image
from typing import Dict, Any
from PyPDF4 import PdfFileReader, PdfFileWriter
from pdf2image import convert_from_bytes
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from telegram import ReplyKeyboardMarkup
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from googletrans import Translator, LANGUAGES
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

TELEGRAM_API_KEY = consts.TOKEN
OPENAI_API_KEY = consts.API_KEY

pdfmetrics.registerFont(TTFont('FreeSans', 'FreeSans.ttf'))  # Add this line

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

translator = Translator()
pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'  # Replace with the path to your Tesseract executable

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Hi! Send me an image, text, or PDF and i will translate it to EN.\n"
        "Here are some hints to help you use this bot:\n\n"
        "1. Choose a target language: Use the /menu_language command to select the language you want to translate to.\n"
        "2. OCR text:Type '/ocr_file', send an image or PDF containing text, and the bot will recognize the text and translate it to the chosen language.\n\n"
        "Send me an image, text, or PDF to translate it to your chosen language."
        "3. Type '/menu_output_format' to choose a format of answer from bot (text of pdf file)\n"
        "4. Type '/help' to show all commands"
    )
    reply_markup=language_keyboard()
    

def help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Here are some hints to help you use this bot:\n\n"
        "1. Choose a target language: Use the /menu_language command to select the language you want to translate to.\n"
        "2. OCR text:Type '/ocr_file', send an image or PDF containing text, and the bot will recognize the text and translate it to the chosen language.\n\n"
        "Send me an image, text, or PDF to translate it to your chosen language."
        "3. Type '/menu_output_format' to choose a format of answer from bot (text of pdf file)"
    )
    update.message.reply_text(help_text)

def language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="en"),
            InlineKeyboardButton("Russian", callback_data="ru"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def format_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("Text", callback_data="text"),
            InlineKeyboardButton("PDF", callback_data="pdf"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def options_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="en"),
            InlineKeyboardButton("Russian", callback_data="ru"),
            InlineKeyboardButton("Dutch", callback_data="nl"),
        ],
        [
            InlineKeyboardButton("German", callback_data="de"),
            InlineKeyboardButton("Spanish", callback_data="es"),
            InlineKeyboardButton("Italian", callback_data="it"),
        ],
        [
            InlineKeyboardButton("Arabic", callback_data="ar"),
            InlineKeyboardButton("French", callback_data="fr"),
            InlineKeyboardButton("Norwegian", callback_data="no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirmation_keyboard(target_language: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("yes", callback_data="yes"),
            InlineKeyboardButton("no", callback_data="no"),
        ],
        
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Set the target language as the detected language if the user has already chosen a language
    if target_language:
        for row in reply_markup.inline_keyboard[1:]:
            for button in row:
                if button.callback_data == target_language:
                    button.text = f"✅ {button.text}"

    return reply_markup


def handle_language_confirmation(update: Update, context: CallbackContext, detected_language: str, img_or_images, target_language: str) -> None:
    message = update.message.reply_text(
        f"Detected language: {detected_language}. Is this correct?",
        reply_markup=confirmation_keyboard(target_language),
    )

    context.user_data["detected_language"] = detected_language
    context.user_data["img_or_images"] = img_or_images
    context.user_data["confirmation_message_id"] = message.message_id


def ocr_translate(img, target_language):
    text = pytesseract.image_to_string(img, lang='ukr')

    # Add this check to validate the target language code
    if target_language not in googletrans.LANGUAGES:
        return f"Error: Invalid target language '{target_language}'. Please choose a valid language code."

    try:
        translation = translator.translate(text, src='uk', dest=target_language).text
        return f'Translation from ukr to {target_language}: {translation}'
    except TypeError:
        return "Error: Unable to translate text. Please try again."


def ocr_file(update: Update, context: CallbackContext) -> None:
    reply_markup = ReplyKeyboardMarkup([["Cancel"]], one_time_keyboard=True)
    update.message.reply_text("Please, send me the image or PDF file you would like to OCR.", reply_markup=reply_markup)

    # Use the message handler to handle OCR files
    context.dispatcher.add_handler(MessageHandler(Filters.all, handle_ocr_file, pass_user_data=True))

def handle_ocr_file(update: Update, context: CallbackContext) -> None:
    if update.message.text == "Cancel":
        update.message.reply_text("Canceled.")
        return

    if update.message.photo:
        handle_image(update, context)
    elif update.message.document and update.message.document.file_name.lower().endswith('.pdf'):
        handle_document(update, context)
    else:
        update.message.reply_text('Please send a valid image or PDF file.')

    # Remove the message handler after processing the OCR file
    context.dispatcher.remove_handler(MessageHandler(Filters.all, handle_ocr_file, pass_user_data=True))
    
def process_translation(update: Update, context: CallbackContext) -> None:
    target_language = context.user_data.get("target_language", "en")
    img_or_images = context.user_data["img_or_images"]

    if isinstance(img_or_images, Image.Image):
        lang, text = ocr_translate(img_or_images, target_language)
        translation = translator.translate(text, dest=target_language).text
        reply_text = f'Translation from {lang} to {target_language}: {translation}'
        send_translation(update, context, reply_text, filename="image_translation.pdf")
    elif isinstance(img_or_images, list):
        translations = []

        for idx, img in enumerate(img_or_images):
            lang, text = ocr_translate(img, target_language)
            translation = translator.translate(text, dest=target_language).text
            translations.append(f'Page {idx + 1}:\nTranslation from {lang} to {target_language}: {translation}')

        reply_text = "\n\n".join(translations)
        send_translation(update, context, reply_text, filename="all_translated_pages.pdf")

    
def handle_format_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    output_format = query.data

    context.user_data["output_format"] = output_format

    query.edit_message_text(
        text=f"Selected output format: {output_format}. Now send me an image, text, or PDF to translate."
    )

def add_watermark(c, watermark_text="Machine translation", x=70, y=70, font="Helvetica", font_size=50, opacity=0.1):
    c.saveState()
    c.setFillColorRGB(0, 0, 0, alpha=opacity)
    c.setFont(font, font_size)
    c.rotate(30)  # Adjust the angle of the watermark
    c.drawString(x, y, watermark_text)
    c.restoreState()
    
def handle_language_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    target_language = query.data

    context.user_data["target_language"] = target_language

    query.edit_message_text(
        text=f"Selected language: {target_language}. Now send me an image, text, or PDF to translate.")

def handle_confirmation(update: Update, context: CallbackContext) -> None:
    confirmed = query.data == "yes"
    rejected = query.data == "no"
    query = update.callback_query
    query.answer()


    if confirmed:
        target_language = context.user_data["target_language"]
        img_or_images = context.user_data["img_or_images"]
        detected_language = context.user_data["detected_language"]

        # # Set the target_language as the detected_language if the user has not chosen a language yet
        # if not target_language:
        #     target_language = detected_language

        # Translate the PDF/image
        process_translation(update, context)
    elif rejected:
        target_language = context.user_data["target_language"]
        img_or_images = context.user_data["img_or_images"]
        query.edit_message_text(
        text=language_keyboard()
    )
        

    else:
        update.effective_chat.send_message("Please choose the correct language:", reply_markup=language_keyboard())

    # Remove the confirmation message
    confirmation_message_id = context.user_data["confirmation_message_id"]
    update.effective_chat.delete_message(confirmation_message_id)



def send_translation(update: Update, context: CallbackContext, reply_text: str, filename="translation.pdf"):
    output_format = context.user_data.get("output_format", "text")

    if output_format == "text":
        update.effective_message.reply_text(reply_text)
    else:
        send_pdf(update, context, reply_text, filename=filename)


def send_pdf(update, context, text, filename="translation.pdf"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    c.setFont("FreeSans", 12)  # Change font to FreeSans

    max_width = 750
    lines = textwrap.wrap(text, width=100)

    x, y = 50, 500
    for line in lines:
        c.drawString(x, y, line)
        y -= 15

    add_watermark(c)  # Add the watermark before saving
    c.save()
    buffer.seek(0)
    context.bot.send_document(chat_id=update.effective_chat.id, document=buffer, filename=filename)


def handle_text(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    target_language = context.user_data.get("target_language", "en")
    lang = translator.detect(text).lang
    translation = translator.translate(text, dest=target_language).text

    reply_text = f'Translation from {lang}: {translation}'
    send_translation(update, context, reply_text)

def handle_image(update: Update, context: CallbackContext) -> None:
    image_url = update.message.photo[-1].get_file().file_path
    response = requests.get(image_url)
    img = Image.open(io.BytesIO(response.content))
    target_language = context.user_data.get("target_language", "en")
    detected_language, _ = ocr_translate(img, target_language)

    handle_language_confirmation(update, context, detected_language, img)

def handle_document(update: Update, context: CallbackContext) -> None:
    document = update.message.document
    if document.file_name.lower().endswith('.pdf'):
        file = context.bot.get_file(update.message.document.file_id)
        pdf_data = io.BytesIO()
        file.download(out=pdf_data)
        images = convert_from_bytes(pdf_data.getvalue())

        # Use the first page to detect the language
        target_language = context.user_data.get("target_language", "en")
        detected_language, _ = ocr_translate(images[0], target_language)

        handle_language_confirmation(update, context, detected_language, images, target_language)  # pass target_language to handle_language_confirmation
    else:
        update.message.reply_text('Unsupported document type.')

def menu_output_format(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Choose an output format:", reply_markup=format_keyboard())
        
def menu_language(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Choose a language to translate to:", reply_markup=language_keyboard(),
)

def main() -> None:
    updater = Updater(TELEGRAM_API_KEY)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("ocr_file", ocr_file))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dispatcher.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^[a-z]{2}$"))
    dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.command, handle_image))
    dispatcher.add_handler(MessageHandler(Filters.document & ~Filters.command, handle_document))
    dispatcher.add_handler(CommandHandler("menu_output_format", menu_output_format))
    dispatcher.add_handler(CallbackQueryHandler(handle_format_selection, pattern="^(text|pdf)$"))
    dispatcher.add_handler(CallbackQueryHandler(handle_confirmation, pattern="^(yes|no)$"))
    dispatcher.add_handler(CommandHandler("menu_language", menu_language))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
    
    
    
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #   
