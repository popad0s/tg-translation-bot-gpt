# import os
# import tempfile
# from pdf2image import convert_from_path
# import telegram
# import constants as consts
# from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
# import pytesseract
# from langdetect import detect
# from googletrans import Translator

# bot = telegram.Bot(consts.TOKEN)

# def start(update, context):
#     update.message.reply_text('Hi, send me a file to translate!')

# def file_handler(update, context):
#     file = context.bot.get_file(update.message.document.file_id)

#     with tempfile.NamedTemporaryFile() as tf:
#         file.download(tf.name)

#         if update.message.document.mime_type in ['image/jpeg', 'image/png', 'image/jpg']:
#             text = pytesseract.image_to_string(tf.name)
#         elif update.message.document.mime_type == 'application/pdf':
#             images = convert_from_path(tf.name)
#             text = ''
#             for img in images:
#                 text += pytesseract.image_to_string(img)
#         else:
#             update.message.reply_text("Unsupported file format. Please send a JPEG, PNG, JPG, or PDF file.")
#             return

#     language = detect(text)
#     translator = Translator()
#     translated_text = translator.translate(text, dest='en').text
#     update.message.reply_text(translated_text)

# updater = Updater(consts.TOKEN, use_context=True)
# dispatcher = updater.dispatcher

# dispatcher.add_handler(CommandHandler('start', start))
# dispatcher.add_handler(MessageHandler(Filters.document.mime_type(['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']), file_handler))

# updater.start_polling()
# updater.idle()

import os
import tempfile
from io import BytesIO

import cv2
import openai
import logging
import pytesseract
from langdetect import detect
from pdf2image import convert_from_bytes
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import constants as consts

# Set your API keys
TELEGRAM_API_KEY = consts.TOKEN
OPENAI_API_KEY = consts.API_KEY

openai.api_key = OPENAI_API_KEY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Hi! Send me an image or PDF file, and I will OCR the text and translate it.')

def image_to_text(image):
    img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(img)
    return text

def pdf_to_text(pdf_data):
    text = []
    images = convert_from_bytes(pdf_data)
    for image in images:
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        text.append(image_to_text(img))
    return ' '.join(text)

def translate_text(text, target_language='en'):
    response = openai.Completion.create(
        engine="davinci-codex",
        prompt=f"Translate the following text to {target_language}:\n\n{text}",
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.7,
    )

    result = response.choices[0].text.strip()
    return result

def document_handler(update: Update, context: CallbackContext):
    file = update.message.document.get_file()
    file_extension = file.file_path.split('.')[-1].lower()
    input_file = BytesIO(file.download_as_bytearray())

    if file_extension in ['jpg', 'jpeg', 'png']:
        image = cv2.imdecode(np.frombuffer(input_file.read(), np.uint8), cv2.IMREAD_UNCHANGED)
        text = image_to_text(image)
    elif file_extension == 'pdf':
        text = pdf_to_text(input_file.read())
    else:
        update.message.reply_text('Unsupported file type. Please send a JPEG, JPG, PNG, or PDF file.')
        return

    if not text.strip():
        update.message.reply_text('No text was detected in the image or PDF file.')
        return

    detected_language = detect(text)
    if detected_language == 'en':
        translated_text = text
    else:
        translated_text = translate_text(text, target_language='en')

    update.message.reply_text(translated_text)

def main():
    updater = Updater(TELEGRAM_API_KEY)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.document, document_handler))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
