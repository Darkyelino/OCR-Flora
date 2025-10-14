import re
import pandas as pd

texto_bruto = """
FEDERAL Saiversirade d0 H ;R BARIO Rog 0%4 336 RIO BRANCO
FLORA DO ACRE
UNIVERSIDALE FEDERAL DO ACRE THE NEW YORK BOTANICAL GARDEN
HELICONIACEAE
Brasil, Acre,   Município de Acrelânida; Br. 364 KM.85, 90957'27,4"S 67024W, fazenda particular de propriedade do Sr. Natalicio Gomes Silva. Terra firme.
Herbácea de 2m. '8 com flores alaranjada
N.V
Rivero, L.S.com 255 11/02/2000 Lima; LA Oliveira; EC. e Mitoso; P
"""

def parse_texto_ocr(texto):
    """
    Função que recebe o texto bruto do OCR e retorna um dicionário
    com os dados estruturados.
    """
    # Inicializa o dicionário com todos os campos vazios. Boa prática!
    dados_planta = {
        'family': '', 'country': '', 'majorarea': '', 'minorarea': '',
        'gazetteer': '', 'locnotes': '', 'habitattxt': '', 'lat': '', 'NS': '',
        'long': '', 'EW': '', 'plantdesc': '', 'vernacular': '',
        'collector': '', 'number': '', 'colldd': '', 'collmm': '', 'collyy': '',
        'addcoll': ''
    }

    # Divide o texto em linhas para facilitar a análise
    linhas = texto.strip().split('\n')

    # --- ESTRATÉGIAS DE EXTRAÇÃO ---

    match = re.search(r'\b([A-Z]{2,})ACEAE\b', texto)
    if match:
        dados_planta['family'] = match.group(0)

    for linha in linhas:
        if "brasil" in linha.lower():
            # País
            dados_planta['country'] = 'Brasil'
            
            # Estado (majorarea)
            if "acre" in linha.lower():
                dados_planta['majorarea'] = 'Acre'

            # Município (minorarea)
            match = re.search(r'Município de ([^;]+)', linha, re.IGNORECASE)
            if match:
                dados_planta['minorarea'] = match.group(1).strip()
            
            # Habitat
            if "terra firme" in linha.lower():
                dados_planta['habitattxt'] = "Terra firme"
            
            # Coordenadas (Latitude e Longitude)
            # Regex para Lat: (números)'(números),(números)"(S|N)
            match_lat = re.search(r'(\d+)\D+(\d+)\D+(\d+[\.,]\d+)\D*([SN])', linha, re.IGNORECASE)
            if match_lat:
                # Junta os números e remove símbolos
                dados_planta['lat'] = f"{match_lat.group(1)}{match_lat.group(2)}{match_lat.group(3)}".replace(',','').replace('.','')
                dados_planta['NS'] = match_lat.group(4).upper()
            
            # Regex para Long: (números)(W|E)
            match_long = re.search(r'(\d+)\D*([WE])', linha, re.IGNORECASE)
            if match_long:
                 dados_planta['long'] = match_long.group(1)
                 dados_planta['EW'] = match_long.group(2).upper()

            # Gazetteer (o que sobrou da localização)
            match_gaz = re.search(r'Br[.]? ?\d+[^,]+', linha, re.IGNORECASE)
            if match_gaz:
                dados_planta['gazetteer'] = match_gaz.group(0)
    
    for linha in linhas:
        if any(keyword in linha.lower() for keyword in ['herbácea', 'árvore', 'arbusto', 'm.']):
             dados_planta['plantdesc'] = linha.strip()

    if 'N.V' in texto:
        dados_planta['vernacular'] = ''

    # Regex: (Nome, I.) [texto lixo] (Número) (Data) (Resto da linha)
    match = re.search(r'([A-Za-z\s,.]+?,\s*[A-Z\.]+)\.?[a-z]*\s+(\d+)\s+(\d{1,2}/\d{1,2}/\d{4})\s?(.*)', texto)
    if match:
        dados_planta['collector'] = match.group(1).strip()
        dados_planta['number'] = match.group(2).strip()
        
        # Quebra a data
        data = match.group(3).strip().split('/')
        dados_planta['colldd'] = data[0]
        dados_planta['collmm'] = data[1]
        dados_planta['collyy'] = data[2]
        
        dados_planta['addcoll'] = match.group(4).strip()

    return dados_planta


# --- EXECUÇÃO E RESULTADO ---

# Chama a função com texto
dados_extraidos = parse_texto_ocr(texto_bruto)

# Imprime o resultado de forma legível
import json
print(json.dumps(dados_extraidos, indent=4, ensure_ascii=False))

# Para salvar no Excel (passo final)
# df = pd.DataFrame([dados_extraidos])
# df.to_excel("dados_extraidos.xlsx", index=False)