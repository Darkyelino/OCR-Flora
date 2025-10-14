import easyocr
import os

os.environ['EASYOCR_LOGGER'] = 'ERROR'

reader = easyocr.Reader(['pt']) 

caminho_imagem = 'EXEMPLO-REAL.jpg' 

resultado = reader.readtext(caminho_imagem, paragraph=True)

print("--- Texto Bruto Extraído ---")
for texto in resultado:
    print(texto[1])