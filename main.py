import easyocr
import os

# Desativa avisos de log que podem poluir a saída
os.environ['EASYOCR_LOGGER'] = 'ERROR'

# Crie um leitor de OCR para o idioma português
# O EasyOCR fará o download do modelo do idioma na primeira vez que for executado
reader = easyocr.Reader(['pt']) 

# Caminho para a sua imagem de teste
caminho_imagem = 'image.png' 

# Extrai o texto da imagem
resultado = reader.readtext(caminho_imagem, paragraph=True)

# Imprime o texto extraído
print("--- Texto Bruto Extraído ---")
for texto in resultado:
    print(texto[1]) # O texto fica na segunda posição da tupla