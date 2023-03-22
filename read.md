<h1>Telegram OCR Translation Bot</h1>

This Telegram bot performs OCR (Optical Character Recognition) and translation on user inputs, which can be text, images, or PDFs. It translates the content to English using the Google Translate API and sends the translated content back as a PDF.

<h3>Table of Contents</h3>

<div style="display: flex; flex-direction: column; margin-right: 10px">
  <div><a href="features">Features</a></div>
  <div><a href="deps">Dependencies</a></div>
  <div><a href="install">Installation and Setup</a></div>
  <div><a href="usage">Usage</a></div>
 </div>
<h3 id="features">Features</h3>

Translates text messages to English and sends the translation as a PDF.
Extracts text from images using OCR, translates it to English, and sends the translation as a PDF.
Extracts text from PDFs using OCR, translates it to English, and sends the translated pages as a single PDF.

<h3='deps'>Dependencies</h3>

<ol>
  <li>pytesseract</li>
  <li>Pillow</li>
  <li>pdf2image</li>
  <li>reportlab</li>
  <li>python-telegram-bot</li>
  <li>googletrans</li>
</ol>

<h3='install'>Installation and Setup</h3>

<div>
  <div>1. Clone the repository or download the code.</div>
  <div>2. Set up a bot on Telegram and obtain the API key.</div>
  <div>3. Store the API key in the constants.py file as TOKEN.</div>
   <div>4. Install the required dependencies using pip:
     
      pip install pytesseract Pillow pdf2image reportlab python-telegram-bot googletrans.</div>
  
  5. Ensure that you have Tesseract OCR installed and set the path in the script.
      
    Run the script:
      python telegram_bot.py
  </div>
<h3 id='usage'>Usage</h3>

<p>1. Search for the bot on Telegram using the bot's username.</p>
<p>2. Initiate a conversation by clicking the "Start" button or typing /start in the chat. The bot will greet you with a message and prompt you to send an image, text, or PDF for translation.</p>
<p>3. To get help or instructions at any time, type /help in the chat. The bot will provide a brief description of its capabilities.
<p>4. Send text directly to the bot by typing a message in the chat. The bot will detect the language, translate it to English, and send the translated text back as a PDF.</p>
<p>5. Send an image containing text to the bot. The bot will perform OCR on the image, detect the language, translate the text to English, and send the translated text as a PDF.</p>
<p>6. Send a PDF document containing text to the bot. The bot will convert the PDF to images, perform OCR on each page, detect the language, translate the text to English, and send the translated pages as a single PDF.</p>

  Remember that the bot is designed to translate text into English. If you wish to support additional languages, you will need to modify the script accordingly.

By following these steps, users can leverage the Telegram bot to translate text, images, or PDFs to English with ease. The bot provides a convenient and accessible way to perform translations on various types of media.



