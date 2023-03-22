import logging
import io
import requests
import textwrap
import constants as consts
import pytesseract
import constants as consts

from PIL import Image
from PyPDF4 import PdfFileReader, PdfFileWriter
from pdf2image import convert_from_bytes
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from googletrans import Translator

TELEGRAM_API_KEY = consts.TOKEN
OPENAI_API_KEY = consts.API_KEY

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

translator = Translator()
pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'  # Replace with the path to your Tesseract executable

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hi! Send me an image, text, or PDF to translate it to EN.')

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Send me an image, text, or PDF to translate it EN.')

def ocr_translate(img):
    text = pytesseract.image_to_string(img)
    lang = translator.detect(text).lang
    translation = translator.translate(text).text
    return f'Translation from {lang}: {translation}'

def add_watermark(c, watermark_text="Machine translation", x=70, y=70, font="Helvetica", font_size=50, opacity=0.1):
    c.saveState()
    c.setFillColorRGB(0, 0, 0, alpha=opacity)
    c.setFont(font, font_size)
    c.rotate(30)  # Adjust the angle of the watermark
    c.drawString(x, y, watermark_text)
    c.restoreState()


def send_pdf(update, context, text, filename="translation.pdf"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    c.setFont("Helvetica", 12)

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
    lang = translator.detect(text).lang
    translation = translator.translate(text).text
    reply_text = f'Translation from {lang}: {translation}'
    send_pdf(update, context, reply_text)

def handle_image(update: Update, context: CallbackContext) -> None:
    image_url = update.message.photo[-1].get_file().file_path
    response = requests.get(image_url)
    img = Image.open(io.BytesIO(response.content))
    reply_text = ocr_translate(img)
    send_pdf(update, context, reply_text, filename="image_translation.pdf")


def handle_document(update: Update, context: CallbackContext) -> None:
    document = update.message.document
    if document.file_name.lower().endswith('.pdf'):
        file = context.bot.get_file(update.message.document.file_id)
        pdf_data = io.BytesIO()
        file.download(out=pdf_data)
        images = convert_from_bytes(pdf_data.getvalue())

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        c.setFont("Helvetica", 12)

        # Read the original PDF
        original_pdf = PdfFileReader(pdf_data)
        output_pdf = PdfFileWriter()

        for idx, img in enumerate(images):
            reply_text = f'Page {idx + 1}:\n{ocr_translate(img)}'
            lines = textwrap.wrap(reply_text, width=100)

            x, y = 50, 500
            for line in lines:
                c.drawString(x, y, line)
                y -= 15

            add_watermark(c)  # Add the watermark before showing the next page or saving
            if idx < len(images) - 1:
                c.showPage()

        c.save()
        buffer.seek(0)

        # Create the translated PDF
        translated_pdf = PdfFileReader(buffer)

        for i in range(translated_pdf.getNumPages()):
            output_pdf.addPage(translated_pdf.getPage(i))

        # Merge the original PDF and translated PDF
        for i in range(original_pdf.getNumPages()):
            output_pdf.addPage(original_pdf.getPage(i))
        
        # Save the merged PDF
        merged_pdf_buffer = io.BytesIO()
        output_pdf.write(merged_pdf_buffer)
        merged_pdf_buffer.seek(0)

        context.bot.send_document(chat_id=update.effective_chat.id, document=merged_pdf_buffer, filename="all_translated_pages.pdf")
    else:
        update.message.reply_text('Unsupported document type.')



def main() -> None:
    updater = Updater(TELEGRAM_API_KEY)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.command, handle_image))
    dispatcher.add_handler(MessageHandler(Filters.document & ~Filters.command, handle_document))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()