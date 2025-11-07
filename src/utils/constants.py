"""Constantes e configurações do CapacitIA."""

# Cores do tema (mantendo as cores atuais do CapacitIA Servidores)
COLORS = {
    'background': '#11142a',
    'panel': '#11142a',
    'muted': '#7780a1',
    'text': '#e6e7ee',
    'primary': '#7DD3FC',  # Azul claro
    'secondary': '#34D399',  # Verde
    'border': '#1e2443',
    'bg': '#0f1220',
}

# Informações dos módulos
MODULES = {
    'servidores': {
        'name': 'CapacitIA Servidores',
        'icon': '👥',
        'description': 'Capacitação em Inteligência Artificial para servidores públicos. O programa oferece treinamentos, workshops e masterclasses sobre IA, preparando os servidores o uso de IA.',
        'page': '2_👥_Servidores',
        'color_primary': '#7DD3FC',
        'color_secondary': '#34D399',
    },
    'saude': {
        'name': 'CapacitIA Saúde',
        'icon': '🏥',
        'description': 'Programa especializado de capacitação em Inteligência Artificial para profissionais da área da saúde do Estado do Piauí. Treinamentos práticos sobre aplicações de IA na saúde.',
        'page': '3_🏥_Saúde',
        'color_primary': '#7DD3FC',
        'color_secondary': '#34D399',
    },
    'autonomia_digital': {
        'name': 'CapacitIA Autonomia Digital',
        'icon': '📱',
        'description': 'Programa de inclusão digital voltado para cidadãos, especialmente idosos e pessoas em situação de vulnerabilidade. Ensina habilidades básicas de tecnologia e acesso a serviços digitais.',
        'page': '4_📱_Autonomia_Digital',
        'color_primary': '#7DD3FC',
        'color_secondary': '#34D399',
    },
}

# Textos descritivos
TEXTS = {
    'sobre_capacitia': """
    O CapacitIA é uma iniciativa da Secretaria de Inteligência Artificial do Piauí (SIA) 
    que visa transformar o serviço público através da capacitação em tecnologias de ponta 
    e inclusão digital. O programa oferece treinamentos especializados em Inteligência 
    Artificial, tecnologias digitais e habilidades básicas de tecnologia, preparando tanto 
    servidores públicos quanto cidadãos para o futuro digital.
    """,
    'servidores': """
    O CapacitIA Servidores é um programa de capacitação em Inteligência Artificial voltado 
    para servidores públicos estaduais. Através de masterclasses, workshops e treinamentos 
    práticos, o programa prepara os servidores para aplicar tecnologias de IA no setor público, 
    melhorando a eficiência e a qualidade dos serviços prestados à população. O programa já 
    capacitou mais de 1.000 servidores de diversas secretarias estaduais.
    """,
    'saude': """
    O CapacitIA Saúde é um programa especializado de capacitação em Inteligência Artificial 
    para profissionais da área da saúde do Estado do Piauí. O programa oferece treinamentos 
    práticos sobre aplicações de IA na saúde, incluindo análise de dados médicos, diagnóstico 
    assistido e gestão hospitalar inteligente. O programa é realizado em lotes, permitindo 
    um acompanhamento personalizado de cada turma.
    """,
    'autonomia_digital': """
    O CapacitIA Autonomia Digital é um programa de inclusão digital voltado para cidadãos, 
    especialmente idosos e pessoas em situação de vulnerabilidade. O programa ensina habilidades 
    básicas de uso de tecnologia, acesso a serviços digitais do governo, proteção contra golpes 
    virtuais e uso de inteligência artificial no cotidiano. O programa já beneficiou mais de 
    140 cidadãos, com alta taxa de satisfação (4.8/5 estrelas).
    """,
}

# Alias para compatibilidade com arquivos existentes
DESCRIPTIONS = {
    'geral': TEXTS['sobre_capacitia'],
    'servidores': TEXTS['servidores'],
    'saude': TEXTS['saude'],
    'autonomia_digital': TEXTS['autonomia_digital'],
}
