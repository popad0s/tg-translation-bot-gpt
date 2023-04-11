import logging
import io
import requests
import textwrap
import constants as consts
import pytesseract
import googletrans

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #  

from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from pdfrw import PdfReader, PdfWriter, IndirectPdfDict
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from telegram import ReplyKeyboardMarkup
from PyPDF4 import PdfFileReader, PdfFileWriter
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from googletrans import Translator, LANGUAGES
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from reportlab.pdfbase import pdfmetrics
from PIL import ImageDraw, ImageFont
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
        "2. Type '/menu_output_format' to choose a format of answer from bot (text of pdf file)\n"
        "3. Type '/help' to show all commands"
        # reply_markup=language_keyboard(),
    )

def help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Here are some hints to help you use this bot:\n\n"
        "1. Choose a target language: Use the /menu_language command to select the language you want to translate to.\n"
        "2. Type '/menu_output_format' to choose a format of answer from bot (text of pdf file)"
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

def ocr_translate(img, target_language):
    text = pytesseract.image_to_string(img)

    # Add this check to validate the target language code
    if target_language not in googletrans.LANGUAGES:
        return f"Error: Invalid target language '{target_language}'. Please choose a valid language code."

    try:
        lang = translator.detect(text).lang
        translation = translator.translate(text, dest=target_language).text
        return f'Translation from {lang} to {target_language}: {translation}'
    except TypeError:
        return "Error: Unable to detect language or translate text. Please try again."


def ocr_file(update: Update, context: CallbackContext) -> None:
    reply_markup = ReplyKeyboardMarkup([["Cancel"]], one_time_keyboard=True)
    update.message.reply_text("Please, send me the image or PDF file you would like to OCR.", reply_markup=reply_markup)

    # Use the message handler to handle OCR files
    context.dispatcher.add_handler(MessageHandler(Filters.all, handle_ocr_file, pass_user_data=True))
    
def send_overlayed_pdf(update, context, pdf_data, translations, filename="translation.pdf"):
    # Read the original PDF data
    pdf_data.seek(0)
    pdf = PdfReader(pdf_data)

    # Add translations as annotations
    for page_num, translation in enumerate(translations):
        page = pdf.pages[page_num]
        if not page.Annots:
            page.Annots = []

        page.Annots.append(
            IndirectPdfDict(
                pdf.Info,
                Subtype="FreeText",
                Contents=translation,
                Rect=[50, 50, 500, 500],
                DA="/Helvetica 12 Tf 0 0 0 rg",
                Q=0,
                Border=[0, 0, 1],
            )
        )

    # Write the overlayed PDF
    buffer = io.BytesIO()
    PdfWriter().write(buffer, pdf)
    buffer.seek(0)
    context.bot.send_document(chat_id=update.effective_chat.id, document=buffer, filename=filename)

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



def send_translation(update: Update, context: CallbackContext, reply_text: str, filename="translation.pdf"):
    output_format = context.user_data.get("output_format", "text")

    if output_format == "text":
        update.message.reply_text(reply_text)
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

    page_number = context.user_data.get("page_number", 1)
    reply_text = f'Translation from {lang} to {target_language}, Page {page_number}: {translation}'
    send_translation(update, context, reply_text)
    context.user_data["page_number"] = page_number + 1


def handle_image(update: Update, context: CallbackContext) -> None:
    image_url = update.message.photo[-1].get_file().file_path
    response = requests.get(image_url)
    img = Image.open(io.BytesIO(response.content))
    target_language = context.user_data.get("target_language", "en")
    reply_text = ocr_translate(img, target_language)

    send_translation(update, context, reply_text, filename="image_translation.pdf")

from PyPDF2 import PdfReader
from pdf2image import convert_from_path

def handle_document(update: Update, context: CallbackContext) -> None:
    document = update.message.document
    if document.file_name.lower().endswith('.pdf'):
        file = context.bot.get_file(update.message.document.file_id)
        pdf_data = io.BytesIO()
        file.download(out=pdf_data)
        
        # Save the PDF to a temporary file
        with open("temp.pdf", "wb") as f:
            f.write(pdf_data.getvalue())
        
        # Get the number of pages in the PDF
        pdf_reader = PdfReader("temp.pdf")
        num_pages = len(pdf_reader.pages)
        
        # Convert the PDF pages to images
        images = convert_from_path("temp.pdf")
        
        # Perform OCR and translation on each image
        translations = []
        for img in images:
            target_language = context.user_data.get("target_language", "en")
            translation_text = ocr_translate(img, target_language)
            translations.append(translation_text)
        
        # Create a new PDF with the translations
        pdf_writer = PdfFileWriter()
        for i, img in enumerate(images):
            # Overlay the translation on the image
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype("FreeSans.ttf", 16)
            draw.multiline_text((50, 50), translations[i], fill=(0, 0, 0), font=font)

            # Convert the image back to a PDF page
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PDF")
            img_buffer.seek(0)
            img_pdf = PdfFileReader(img_buffer)
            pdf_writer.addPage(img_pdf.getPage(0))

        # Send the new PDF with the translations
        buffer = io.BytesIO()
        pdf_writer.write(buffer)
        buffer.seek(0)
        context.bot.send_document(chat_id=update.effective_chat.id, document=buffer, filename="translated.pdf")
    else:
        update.message.reply_text('Unsupported document type.')
  
def send_merged_pdf(update, context, texts, filename="translation.pdf"):
    buffer = io.BytesIO()
    pdf_writer = PdfFileWriter()

    for text in texts:
        page_buffer = io.BytesIO()
        c = canvas.Canvas(page_buffer, pagesize=landscape(letter))
        c.setFont("FreeSans", 12)

        max_width = 750
        lines = textwrap.wrap(text, width=100)

        x, y = 50, 500
        for line in lines:
            c.drawString(x, y, line)
            y -= 15

        add_watermark(c)
        c.showPage()
        c.save()
        page_buffer.seek(0)

        page_pdf = PdfFileReader(page_buffer)
        pdf_writer.addPage(page_pdf.getPage(0))

    with buffer:
        pdf_writer.write(buffer)
        buffer.seek(0)
        context.bot.send_document(chat_id=update.effective_chat.id, document=buffer, filename=filename)

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
    dispatcher.add_handler(CommandHandler("menu_language", menu_language))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()