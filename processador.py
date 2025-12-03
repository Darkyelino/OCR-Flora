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

PALAVRAS_IGNORADAS = [
    "ACRE", "BRASIL", "AMAZONIA", "FLORA", "PROJETO", "UNIVERSIDADE", "FEDERAL", "ESTADUAL", 
    "INSTITUTO", "JARDIM", "BOTANICO", "HORTUS", "MUSEU", "COLECAO", "COLEÇÃO", "LABORATORIO",
    "PROGRAMA", "PREFEITURA", "SECRETARIA", "DIRECAO", "DIREÇÃO", "COORDENACAO", "COORDENAÇÃO",
    "CAPES", "CNPQ", "FAPEAC", "GOVERNO", "MINISTERIO", "MINISTÉRIO", "PESQUISA", "DEPARTAMENTO",
    "EX-REAL", "MUNICÍPIO", "MUNICIPIO", "MUN", "MUNIC", "ESTADO", "RODOVIA", "ESTRADA", "FAZENDA", 
    "SÍTIO", "SITIO", "CHÁCARA", "CHACARA", "RAMAL", "IGARAPÉ", "IGARAPE", "RIO", "FLORESTA",
    "MATO", "PARQUE", "RESERVA", "ÁREA", "AREA", "PRÓXIMO", "PROXIMO", "ENTRE", "LIMITE",
    "COMUNIDADE", "VILA", "ZONA", "URBANA", "RURAL", "SUL", "NORTE", "LESTE", "OESTE", "CENTRO",
    "DATA", "COLETA", "NÚMERO", "NUMERO", "Nº", "NO", "LATITUDE", "LONGITUDE", "COORDENADAS",
    "LAT", "LONG", "ALT", "ALTURA", "METROS", "M", "KM", "HERBARIO", "HERB", "DET", "DETERMINADOR", 
    "FAMILIA", "FAMILY", "NOME", "VULGAR", "ESPÉCIE", "ESPECIE", "GÊNERO", "GENERO", "G", "COM", 
    "FLORES", "FRUTOS", "PLANTAS", "SEMENTES", "ARVORE", "ÁRVORE", "ARBUSTO", "HERBÁCEA", 
    "CAULE", "FOLHA", "TRONCO", "N.V", "N.V.", "OCCASIONAL", "SECONDARY", "FOREST", "TREE", 
    "FRUITS", "WARTY", "FIELD", "WORK", "SUPPORTED", "FOUNDATION", "PROPERTY", "OWNER"
]

SOBRENOMES_COMUNS = [
    "SILVA", "SANTOS", "OLIVEIRA", "SOUZA", "RODRIGUES", "FERREIRA", "ALVES", "PEREIRA", 
    "LIMA", "GOMES", "COSTA", "RIBEIRO", "MARTINS", "CARVALHO", "ALMEIDA", "LOPES", 
    "SOARES", "FERNANDES", "VIEIRA", "BARBOSA", "ROCHA", "DIAS", "NASCIMENTO", "ANDRADE", 
    "MOREIRA", "NUNES", "MARQUES", "MACHADO", "MENDES", "FREITAS", "CARDOSO", "RAMOS", 
    "GONÇALVES", "GONCALVES", "REIS", "TEIXEIRA", "MOTA", "SANTANA", "VIDAL", "MACEDO", 
    "DANTAS", "CASTRO", "ARAUJO", "ARAÚJO", "MELO", "MELLO", "CAVALCANTE", "SERRA", "CAMPOS",
    "FIGUEIREDO", "RIVERO", "DALY", "PRANCE", "CID", "FERREIRA", "MITOSO", "SILVEIRA",
    "EHRINGHAUS", "LOWY", "NELSON", "PLOWMAN", "DAVIDSE", "CROAT", "ANDERSON", "KALIN", 
    "ARROYO", "MORI", "KUBITZKI", "MAAS", "PENNINGTON", "PRANCE"
]

# --- 1. FUNÇÃO DE EXTRAÇÃO DE TEXTO ---
def extrair_texto_com_acuracia(caminho_imagem):
    print(f"\nProcessando imagem: {os.path.basename(caminho_imagem)}")
    try:
        os.environ['EASYOCR_LOGGER'] = 'ERROR'
        reader = easyocr.Reader(['pt', 'en'], gpu=False)
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

# --- 2. "ESPECIALISTAS" AUXILIARES ---
def encontrar_familia(texto):
    match = re.search(r'\b([A-Za-zÀ-ú]{3,})ACEAE\b', texto, re.IGNORECASE)
    return match.group(0) if match else ''

def encontrar_coordenadas(texto):
    lat, ns, long, ew = '', '', '', ''
    texto_limpo = re.sub(r'\s+', ' ', texto)
    match_lat = re.search(r'(\d{1,3})\D+(\d{1,2})\D+(\d{1,2}[\.,]?\d?)\D*([SN])', texto_limpo, re.IGNORECASE)
    if match_lat:
        lat = f"{match_lat.group(1)}{match_lat.group(2)}{match_lat.group(3)}".replace(',','').replace('.','')
        ns = match_lat.group(4).upper()
    match_long = re.search(r'(\d{1,3})\D+(\d{1,2})\D+(\d{1,2}[\.,]?\d?)\D*([WE])', texto_limpo, re.IGNORECASE)
    if match_long:
        long = f"{match_long.group(1)}{match_long.group(2)}{match_long.group(3)}".replace(',','').replace('.','')
        ew = match_long.group(4).upper()
    return lat, ns, long, ew

def encontrar_data_coleta(texto):
    match_num = re.search(r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b', texto)
    if match_num:
        dd, mm, yy = match_num.groups()
        if len(yy) == 2: yy = f"19{yy}" if int(yy) > 50 else f"20{yy}"
        return dd, mm, yy
    
    match_en = re.search(r'([A-Z][a-z]+)\s+(\d{1,2})\s*,\s*(\d{4})', texto)
    if match_en:
        mes_str, dia, ano = match_en.groups()
        meses = {'January':'01', 'February':'02', 'March':'03', 'April':'04', 'May':'05', 'June':'06', 
                 'July':'07', 'August':'08', 'September':'09', 'October':'10', 'November':'11', 'December':'12'}
        mes = meses.get(mes_str, '00')
        return dia, mes, ano

    return '', '', ''

# <-- NOVO ESPECIALISTA INDEPENDENTE DE NÚMERO -->
def encontrar_numero_coleta(texto, data_tuple, lat, long):
    # 1. Estratégia Explícita (Procura por rótulos)
    texto_plano = re.sub(r'\s+', ' ', texto)
    match_explicito = re.search(r'(?:No\.|Nº|Number|Num|#)\s*(\d{1,6})', texto_plano, re.IGNORECASE)
    if match_explicito:
        return match_explicito.group(1)

    # 2. Estratégia de Dedução (Acha números e remove o que já sabemos que é outra coisa)
    # Encontra TODOS os números isolados de 1 a 5 dígitos
    todos_numeros = re.findall(r'\b(\d{1,5})\b', texto_plano)
    
    candidatos = []
    
    # Valores a ignorar (partes da data e coordenadas já encontradas)
    dia, mes, ano = data_tuple
    valores_proibidos = [dia, mes, ano, lat[:2], lat[:3], long[:2], long[:3]]
    valores_proibidos = [v for v in valores_proibidos if v] # Remove vazios

    for num in todos_numeros:
        # Se o número for igual a uma parte da data ou coordenada, ignora
        if num in valores_proibidos: continue
        
        # Ignora anos óbvios se estiverem isolados (ex: 1998, 2005)
        if len(num) == 4 and (num.startswith('19') or num.startswith('20')):
            continue
            
        candidatos.append(num)

    # Se sobrou algum candidato...
    if candidatos:
        # Prioriza o maior número (geralmente numeração de coleta é crescente e maior que dias/meses)
        # OU o último encontrado antes da data (mas como o texto é plano, difícil saber).
        # Vamos pegar o candidato que tem mais dígitos, pois geralmente é o identificador único
        return max(candidatos, key=len)
        
    return ''

# --- ESPECIALISTA DE COLETOR (AGORA FOCADO SÓ EM NOMES) ---
def encontrar_coletor_info(texto):
    texto_plano = re.sub(r'\s+', ' ', texto)
    collector, addcoll = '', ''

    # Vamos buscar nomes candidatos usando a Lista Branca como "imã"
    palavras = texto_plano.split()
    
    melhor_candidato = ""
    melhor_score = 0

    # Varre janelas de palavras procurando sobrenomes conhecidos
    for i in range(len(palavras)):
        word = palavras[i].upper().replace(',', '').replace('.', '')
        
        # Se a palavra é um sobrenome comum, olhamos em volta
        if word in SOBRENOMES_COMUNS:
            # Tenta pegar "Nome Sobrenome" (palavra anterior + atual)
            inicio = max(0, i-2)
            fim = min(len(palavras), i+2)
            fragmento = " ".join(palavras[inicio:fim])
            
            # Limpa lixo do fragmento
            fragmento = re.sub(r'[\d;:!@#$%^&*()_+={}\[\]|\\:"]', '', fragmento).strip()
            
            # Valida
            if validar_nome_coletor(fragmento):
                # Se achou algo válido que contem um sobrenome comum, é um forte candidato
                # Preferimos o que aparece primeiro ou o mais completo?
                # Vamos pegar o primeiro válido encontrado que tenha tamanho razoável
                if len(fragmento) > len(melhor_candidato):
                    melhor_candidato = fragmento

    if melhor_candidato:
        collector = melhor_candidato
    else:
        # Fallback: Tenta achar pela data (Âncora) se a busca por sobrenome falhou
        padrao_data = r'(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})'
        match_data = re.search(padrao_data, texto_plano, re.IGNORECASE)
        if match_data:
            texto_antes = texto_plano[:match_data.start()].strip()
            # Pega as ultimas palavras antes da data/numero
            palavras_antes = texto_antes.split()
            candidato = " ".join(palavras_antes[-5:])
            # Remove numeros do final (o numero da coleta)
            candidato = re.sub(r'\d+$', '', candidato).strip()
            if validar_nome_coletor(candidato):
                collector = candidato

    # Tenta limpar o collector final de conectores
    collector = re.sub(r'\s+(?:com|et\sal\.?|n[ºo\.]?)$', '', collector, flags=re.IGNORECASE).strip()

    # Busca Addcoll (Co-coletores)
    # Geralmente vem depois do nome principal ou tem "et al"
    if 'et al' in texto_plano.lower():
        addcoll = 'et al.'
    elif collector:
        # Tenta achar o collector no texto original e pegar o que vem depois
        try:
            idx = texto_plano.find(collector)
            if idx != -1:
                resto = texto_plano[idx+len(collector):idx+len(collector)+50]
                # Remove o número da coleta do resto, se houver
                resto = re.sub(r'^\s*[\d\s,.-]+', '', resto).strip()
                if validar_nome_coletor(resto):
                    addcoll = resto
        except: pass

    return collector, addcoll

def validar_nome_coletor(nome):
    if len(nome) < 3: return False
    if not re.search(r'[a-zA-Z]', nome): return False
    
    palavras_nome = nome.upper().replace(',', '').replace('.', '').split()
    locais_proibidos = PALAVRAS_IGNORADAS + [x.upper() for x in MUNICIPIOS_ACRE] + [x.upper() for x in ESTADOS_BRASIL.values()]
    LIMITE_SIMILARIDADE_NEG = 85 

    for p in palavras_nome:
        if len(p) < 3: continue
        melhor_match, score = process.extractOne(p, locais_proibidos)
        if score >= LIMITE_SIMILARIDADE_NEG:
            return False
            
    return True

def encontrar_localizacao(texto):
    country, majorarea, minorarea = '', '', ''
    SIMILARITY_THRESHOLD = 80
    
    texto_plano = re.sub(r'\s+', ' ', texto)

    if 'brasil' in texto.lower() or 'brazil' in texto.lower():
        country = 'Brasil'

    if not minorarea:
        match_abrev = re.search(r'\b([A-Z]{2,})\b\s*[-/]\s*\b(AC)\b', texto_plano, re.IGNORECASE)
        if match_abrev:
            abrev_potencial = match_abrev.group(1).upper()
            best_match_abrev, score = process.extractOne(abrev_potencial, MUNICIPIOS_ABREV.keys())
            if score >= SIMILARITY_THRESHOLD:
                minorarea = MUNICIPIOS_ABREV[best_match_abrev]

    if not minorarea:
        match_prefix = re.search(r'(?:Mun[ií]c[ií]pio\s+de|Mun\.?|Municipality\s+of)\s+([A-Za-z\sÀ-ú]+)', texto_plano, re.IGNORECASE)
        if match_prefix:
            cidade_potencial = match_prefix.group(1).strip()
            best_match, score = process.extractOne(cidade_potencial, MUNICIPIOS_ACRE)
            if score >= SIMILARITY_THRESHOLD:
                minorarea = best_match

    if not minorarea:
        for cidade in MUNICIPIOS_ACRE:
            if re.search(r'\b' + re.escape(cidade) + r'\b', texto_plano, re.IGNORECASE):
                minorarea = cidade
                break

    if minorarea:
        majorarea = 'Acre'
        country = 'Brasil'
    elif not country: 
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
    dados['colldd'], dados['collmm'], dados['collyy'] = encontrar_data_coleta(texto)
    
    # 1. Encontra número INDEPENDENTE
    dados['number'] = encontrar_numero_coleta(texto, (dados['colldd'], dados['collmm'], dados['collyy']), dados['lat'], dados['long'])
    
    # 2. Encontra Coletor INDEPENDENTE
    dados['collector'], dados['addcoll'] = encontrar_coletor_info(texto)
    
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