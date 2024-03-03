from flask import Flask, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
from openai import OpenAI
from markupsafe import escape

import os
import shutil
import asyncio

app = Flask(__name__, static_folder='../static')
CORS(app)  # Enable CORS for all domains on all routes
client = OpenAI(api_key='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')

firstOpinionDict = {}
secondOpinionDict = {}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'test.html')

#Get the first opinion, and store the result for the opinion in a cache to speed up execution for same opinion
@app.route('/firstopinion')
def getFirstOpinion():
  searchText = request.args.get('text','')
  needAudio = request.args.get('audio',False)

  _setup(searchText, 'English')
  model = 'gpt-3.5-turbo'
  return getOpinion(model, searchText,needAudio, 'firstopinion')

#Get the second opinion, and store the result for the opinion in a cache to speed up execution for same opinion
@app.route('/secondopinion')
def getSecondOpinion():
  searchText = request.args.get('text','')
  needAudio = request.args.get('audio',False)
  
  model = 'gpt-4'
  return getOpinion(model, searchText,needAudio, 'secondopinion')

#Get the translated text in a given language
@app.route('/translate/<opinion>')
def getTextInLanguage(opinion):
  opinion = escape(opinion)

  inputText = request.args.get('text','')
  language = request.args.get('language', 'English')
  needAudio = request.args.get('audio',False)
  model = 'gpt-3.5-turbo'
  translatedText = ''
  audioFile = str(Path(__file__).parent) + "/%s/speech_%s.mp3" % (opinion, language)

  if opinion == 'firstopinion' and language in firstOpinionDict and os.path.exists(audioFile):
    translatedText = firstOpinionDict[language]

  elif opinion == 'secondopinion' and language in secondOpinionDict and os.path.exists(audioFile):
    translatedText = secondOpinionDict[language]

  else:
    translatedText = getTranslatedText(inputText, language, model, needAudio, opinion)

    if opinion == 'first':
      firstOpinionDict[language] = translatedText
  
    if opinion == 'second':
      secondOpinionDict[language] = translatedText

  return translatedText

#Get opinion from the chat assistant, if needAudio flag is set generate audio file
def getOpinion(model, question, needAudio, opinion):
  completion = client.chat.completions.create(
  model=model,
  messages=[
    {"role": "system", "content": "Hi! You are now a Therapist. Act like a mental health therapist and help the user with the problem. Make your responses detailed and reflective to help the user and offer suggestions and help. You have to provide suggestions and help. You cannot just say that you can't help."},
    {"role": "user", "content": question}
  ])
  
  responseText = completion.choices[0].message.content

  if needAudio:
    defaultLanguage = 'English'
    filename = "speech_%s.mp3" % (defaultLanguage)
    speech_file_path = str(Path(__file__).parent) + "/%s/%s" % (opinion, filename)
    if not os.path.exists(speech_file_path):
      asyncio.run(createAudioFileForText(responseText, speech_file_path))

  return responseText

#Creat audio file for given text
async def createAudioFileForText(text, filename):
  speech_file_path = filename
  response = client.audio.speech.create(
  model="tts-1",
  voice="alloy",
  input=text
  )
  response.stream_to_file(speech_file_path)

#Get the translated text in a given language for a text
def getTranslatedText(text, language, model, needAudio, opinion):
  contentText = 'Translate the following text to %s: {%s}' % (language, text)
  completion = client.chat.completions.create(
  model=model,
  messages=[
    {"role": "user", "content": contentText}])

  responseText = completion.choices[0].message.content

  if needAudio:
    speech_file_path = str(Path(__file__).parent) + "/%s/speech_%s.mp3" % (opinion, language)
    if not os.path.exists(speech_file_path):
      asyncio.run(createAudioFileForText(responseText, speech_file_path))

  return responseText

@app.route('/audio/<opinion>/<filename>')
def serve_audio(opinion, filename):
    opinion_path = Path(__file__).parent / opinion
    return send_from_directory(opinion_path, filename)


#Setup for the assitant: clear of the caches that store texts to speed up execution
def _setup(question, language):
  if len(firstOpinionDict) > 0 and language in firstOpinionDict:
    existingQuestion = firstOpinionDict[language]
    if existingQuestion != question:
      _clear()
  else:
    _clearAllAudioFiles()
    
        
def _clear():
  firstOpinion.clear()
  secondOpinion.clear() 
  _clearAllAudioFiles()

def _clearAllAudioFiles():
  firstOpinionFolderPath = Path(__file__).parent/"firstopinion"
  _clearAudioFilesForOpinion(firstOpinionFolderPath)

  secondOpinionFolderPath = Path(__file__).parent/"secondopinion"
  _clearAudioFilesForOpinion(secondOpinionFolderPath)

def _clearAudioFilesForOpinion(folder):
  for filename in os.listdir(folder):
    file_path = os.path.join(folder, filename)
    try:
        if os.path.exists(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        print('Failed to delete %s. Reason: %s' % (file_path, e))
