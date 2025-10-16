# -*- coding: utf-8 -*-
import easyocr
import re
import pandas as pd
import os
import numpy as np
from thefuzz import process

# --- CONFIGURAÇÕES E CONSTANTES ---

MUNICIPIOS_ACRE = [
    "Acrelândia", "Assis Brasil", "Brasiléia", "Bujari", "Capixaba",
    "Cruzeiro do Sul", "Epitaciolândia", "Feijó", "Jordão", "Manoel Urbano",
    "Marechal Thaumaturgo", "Mâncio Lima", "Plácido de Castro", "Porto Acre",
    "Porto Walter", "Rio Branco", "Rodrigues Alves", "Santa Rosa do Purus",
    "Sena Madureira", "Senador Guiomard", "Tarauacá", "Xapuri"
]

MUNICIPIOS_ABREV = {
    "AB": "Assis Brasil", "CZ": "Cruzeiro do Sul", "MU": "Manoel Urbano", "MT": "Marechal Thaumaturgo", 
    "ML": "Mâncio Lima", "PC": "Plácido de Castro", "PA": "Porto Acre", 
    "PW": "Porto Walter", "RB": "Rio Branco", "RA": "Rodrigues Alves", 
    "SP": "Santa Rosa do Purus", "SM": "Sena Madureira", "SG": "Senador Guiomard"
}

ESTADOS_BRASIL = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 
    'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 
    'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 
    'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí', 
    'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 
    'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo', 
    'SE': 'Sergipe', 'TO': 'Tocantins'
}

# --- 1. FUNÇÃO DE EXTRAÇÃO DE TEXTO ---
def extrair_texto_com_acuracia(caminho_imagem):
    print(f"\nProcessando imagem: {os.path.basename(caminho_imagem)}")
    try:
        os.environ['EASYOCR_LOGGER'] = 'ERROR'
        reader = easyocr.Reader(['pt'], gpu=False)
        resultado_ocr = reader.readtext(caminho_imagem)
        if not resultado_ocr:
            print(" -> Nenhum texto detectado.")
            return "", 0.0
        texto_completo = "\n".join([res[1] for res in resultado_ocr])
        confiancas = [res[2] for res in resultado_ocr]
        media_confianca = np.mean(confiancas)
        print(f" -> Texto extraído com acurácia média de: {media_confianca:.2%}")
        return texto_completo, media_confianca
    except Exception as e:
        print(f" -> Ocorreu um erro ao processar a imagem: {e}")
        return "", 0.0

# --- 2. "ESPECIALISTAS" EM ENCONTRAR DADOS ---
def encontrar_familia(texto):
    match = re.search(r'\b([A-Za-zÀ-ú]{3,})ACEAE\b', texto, re.IGNORECASE)
    return match.group(0) if match else ''

def encontrar_coordenadas(texto):
    lat, ns, long, ew = '', '', '', ''
    match_lat = re.search(r'(\d{1,3})\D+(\d{1,2})\D+(\d{1,2}[\.,]?\d?)\D*([SN])', texto, re.IGNORECASE)
    if match_lat:
        lat = f"{match_lat.group(1)}{match_lat.group(2)}{match_lat.group(3)}".replace(',','').replace('.','')
        ns = match_lat.group(4).upper()
    match_long = re.search(r'(\d{1,3})\D+(\d{1,2})\D+(\d{1,2}[\.,]?\d?)\D*([WE])', texto, re.IGNORECASE)
    if match_long:
        long = f"{match_long.group(1)}{match_long.group(2)}{match_long.group(3)}".replace(',','').replace('.','')
        ew = match_long.group(4).upper()
    return lat, ns, long, ew

# <-- MUDANÇA AQUI: Novo especialista dedicado a encontrar datas
def encontrar_data_coleta(texto):
    # Procura por qualquer padrão de data (dd/mm/yyyy, dd-mm-yy, etc.)
    matches = re.findall(r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b', texto)
    for match in matches:
        dd, mm, yy = match
        # Validação simples para evitar datas impossíveis (ex: mês 81)
        if 1 <= int(mm) <= 12 and 1 <= int(dd) <= 31:
            # Normaliza o ano para 4 dígitos
            if len(yy) == 2:
                yy = f"20{yy}" if int(yy) < 30 else f"19{yy}"
            return dd, mm, yy
    return '', '', ''

# <-- MUDANÇA AQUI: Especialista de coletor focado apenas em nome e número
def encontrar_coletor_info(texto):
    padroes = [
        # Padrão para "Sobrenome, I." e "Nome Sobrenome et al."
        r'([A-Za-z\s,.-]+?,\s*[A-Z\.]+|[A-Za-z\s,.-]+?et al\.)\s+(\d+)\s?(.*)',
        # Padrão para "Nome Sobrenome" (sem vírgula)
        r'\b([A-Z][a-z]+[A-Z\s,.-]+)\s+(\d{3,})'
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            collector = match.group(1).strip()
            number = match.group(2).strip()
            # O que sobra na linha pode ser um co-coletor
            addcoll = match.group(3).strip() if len(match.groups()) > 2 else ('et al.' if 'et al.' in collector else '')
            return collector, number, addcoll
    return '', '', ''

def encontrar_localizacao(texto):
    country, majorarea, minorarea = '', '', ''
    SIMILARITY_THRESHOLD = 85
    if not minorarea:
        match_abrev = re.search(r'\b([A-Z]{2,})\b\s*[-/]\s*\b(AC)\b', texto, re.IGNORECASE)
        if match_abrev:
            abrev_potencial = match_abrev.group(1).upper()
            best_match_abrev, score = process.extractOne(abrev_potencial, MUNICIPIOS_ABREV.keys())
            if score >= SIMILARITY_THRESHOLD:
                minorarea = MUNICIPIOS_ABREV[best_match_abrev]

    if not minorarea:
        match_prefix = re.search(r'(?:Mun[ií]c[ií]pio\s+de|Mun\.?)\s+([A-Za-z\sÀ-ú]+)', texto, re.IGNORECASE)
        if match_prefix:
            cidade_potencial = match_prefix.group(1).strip()
            best_match, score = process.extractOne(cidade_potencial, MUNICIPIOS_ACRE)
            if score >= SIMILARITY_THRESHOLD:
                minorarea = best_match

    if not minorarea:
        for cidade in MUNICIPIOS_ACRE:
            if re.search(r'\b' + re.escape(cidade) + r'\b', texto, re.IGNORECASE):
                minorarea = cidade
                break

    if minorarea:
        majorarea = 'Acre'
        country = 'Brasil'
    else:
        texto_upper = texto.upper()
        for sigla, nome in ESTADOS_BRASIL.items():
            if f' {sigla} ' in texto_upper or f'-{sigla}' in texto_upper or f' {nome.upper()} ' in texto_upper:
                majorarea = nome
                country = 'Brasil'
                break
                
    return country, majorarea, minorarea

# --- 3. FUNÇÃO ORQUESTRADORA DO PARSER ---
def parse_texto_etiqueta(texto):
    dados = {}
    dados['family'] = encontrar_familia(texto)
    dados['lat'], dados['NS'], dados['long'], dados['EW'] = encontrar_coordenadas(texto)
    # <-- MUDANÇA AQUI: Chamando os especialistas separados
    dados['colldd'], dados['collmm'], dados['collyy'] = encontrar_data_coleta(texto)
    dados['collector'], dados['number'], dados['addcoll'] = encontrar_coletor_info(texto)
    dados['country'], dados['majorarea'], dados['minorarea'] = encontrar_localizacao(texto)
    return dados

# --- 4. FLUXO DE EXECUÇÃO PRINCIPAL ---
def main():
    pasta_imagens = "imagens_para_processar"
    arquivo_saida_excel = "dados_coleta_plantas.xlsx"
    if not os.path.exists(pasta_imagens):
        print(f"Erro: A pasta '{pasta_imagens}' não foi encontrada.")
        return
    lista_resultados = []
    arquivos_imagens = [f for f in os.listdir(pasta_imagens) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not arquivos_imagens:
        print(f"Nenhuma imagem encontrada na pasta '{pasta_imagens}'.")
        return
    for nome_arquivo in arquivos_imagens:
        caminho_completo = os.path.join(pasta_imagens, nome_arquivo)
        texto, acuracia = extrair_texto_com_acuracia(caminho_completo)
        if texto:
            dados_extraidos = parse_texto_etiqueta(texto)
            dados_extraidos['arquivo_origem'] = nome_arquivo
            dados_extraidos['acuracia_ocr'] = f"{acuracia:.2%}"
            dados_extraidos['texto_bruto_ocr'] = texto
            lista_resultados.append(dados_extraidos)
    if not lista_resultados:
        print("\nNenhum dado foi extraído.")
        return
    print(f"\nProcesso finalizado. Salvando {len(lista_resultados)} registros em '{arquivo_saida_excel}'...")
    df = pd.DataFrame(lista_resultados)
    ordem_colunas = [
        'arquivo_origem', 'acuracia_ocr', 'family', 'collector', 'number', 'addcoll',
        'colldd', 'collmm', 'collyy', 'country', 'majorarea', 'minorarea', 
        'lat', 'NS', 'long', 'EW', 'texto_bruto_ocr'
    ]
    colunas_finais = ordem_colunas + [col for col in df.columns if col not in ordem_colunas]
    df = df[colunas_finais]
    df.to_excel(arquivo_saida_excel, index=False)
    print("Arquivo salvo com sucesso!")

if __name__ == "__main__":
    main()