import json
import requests
import pandas as pd
import plotly.graph_objects as go

# 1. Requisição à API
url = "https://royalblue-turtle-204261.hostingersite.com/ws_dados.php?tipo_pesquisa=1"

try:
    response = requests.get(url, timeout=10)
    dataJson = response.json()

    if isinstance(dataJson, dict) and "data" in dataJson:
        rawData = dataJson["data"]
    elif isinstance(dataJson, list):
        rawData = dataJson
    else:
        rawData = []
except Exception as e:
    print("Erro na API, carregando estrutura vazia:", e)
    rawData = []

# 2. DataFrame Pandas e Sanitização
df = pd.DataFrame(rawData)

# Tratamento colunas
if 'quantidade' not in df.columns:
    df['quantidade'] = 0
if 'segmento' not in df.columns:
    df['segmento'] = 'Não Informado'
if 'administradora' not in df.columns:
    df['administradora'] = 'Não Informada'
if 'data_referencia' not in df.columns:
    df['data_referencia'] = '2026-01-01'

# Formatação e limpeza dos dados
df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce').fillna(0).astype(int)
df['segmento'] = df['segmento'].astype(str).str.strip()
df['administradora'] = df['administradora'].astype(str).str.strip()

# 3. Tratamento de data e ordenação cronológica
df['dt_temp'] = pd.to_datetime(df['data_referencia'], errors='coerce')
meses_ordenados_dt = sorted([d for d in df['dt_temp'].dropna().unique()])
variavel_todos_meses = [pd.Timestamp(d).strftime('%m/%Y') for d in meses_ordenados_dt]

# Aplica a formatação definitiva MM/YYYY na coluna de referência
df['data_referencia'] = df['dt_temp'].dt.strftime('%m/%Y').fillna('Indefinido')
df.drop(columns=['dt_temp'], inplace=True)

# Extração de Segmentos e Administradoras
variavel_segmentos = sorted([s for s in df['segmento'].unique() if s and s.lower() != 'nan'])
variavel_administradoras = sorted([a for a in df['administradora'].unique() if a and a.lower() != 'nan'])

# Datas para os rótulos de período
dataInicio = variavel_todos_meses[0] if variavel_todos_meses else "N/A"
dataFim = variavel_todos_meses[-1] if variavel_todos_meses else "N/A"

# -------------------------------------------------------------
# CALCULAR O MELHOR SEGMENTO GLOBAL (ESTÁTICO / FIXO DA BASE INTEIRA)
# -------------------------------------------------------------
df_seg_global = df.groupby('segmento')['quantidade'].sum().reset_index()
df_seg_global = df_seg_global.sort_values(by='quantidade', ascending=False)

if not df_seg_global.empty:
    melhor_seg_global_nome = df_seg_global.iloc[0]['segmento']
    melhor_seg_global_qtd = f"{df_seg_global.iloc[0]['quantidade']:,}".replace(',', '.')
    melhor_seg_global_texto = f"{melhor_seg_global_nome} ({melhor_seg_global_qtd})"
else:
    melhor_seg_global_texto = "N/A"

# -------------------------------------------------------------
# 4. MAPEAMENTO FIXO DE CORES POR SEGMENTO
# -------------------------------------------------------------
paleta_cores = ['#1A4B83', '#28A745', '#E67E22', '#8E44AD', '#17A2B8', '#D9534F', '#F39C12', '#34495E']
mapa_cores_segmentos = {seg: paleta_cores[i % len(paleta_cores)] for i, seg in enumerate(variavel_segmentos)}

# -------------------------------------------------------------
# 5. GERAR LISTA ESTÁTICA DE ADMINISTRADORAS
# -------------------------------------------------------------
df_admin_estatico = df.groupby('administradora')['quantidade'].sum().reset_index()
df_admin_estatico = df_admin_estatico.sort_values(by='quantidade', ascending=False)

lista_admin_html_items = []
for _, row in df_admin_estatico.iterrows():
    nome_admin = row['administradora']
    qtd_admin = f"{row['quantidade']:,}".replace(',', '.')
    item_html = f"""
    <li class="list-group-item d-flex justify-content-between align-items-center py-2 px-3 border-0 border-bottom">
        <span class="fw-semibold text-truncate me-2" style="font-size: 0.85rem;" title="{nome_admin}">{nome_admin}</span>
        <span class="badge bg-primary rounded-pill px-2 py-1" style="font-size: 0.8rem; background-color: var(--primary-red) !important;">{qtd_admin}</span>
    </li>
    """
    lista_admin_html_items.append(item_html)

lista_admin_html = "".join(lista_admin_html_items)

# -------------------------------------------------------------
# 6. CRIAÇÃO DO GRÁFICO PLOTLY EM PYTHON
# -------------------------------------------------------------
fig = go.Figure()

for seg in variavel_segmentos:
    df_seg = df[df['segmento'] == seg]
    agrupado = df_seg.groupby('data_referencia')['quantidade'].sum().to_dict()
    valores = [agrupado.get(m, 0) for m in variavel_todos_meses]

    fig.add_trace(go.Bar(
        x=variavel_todos_meses,
        y=valores,
        name=seg,
        marker_color=mapa_cores_segmentos[seg],
        text=[f"{v:,}".replace(',', '.') if v > 0 else '' for v in valores],
        textposition='outside',
        hovertemplate='<b>%{fullData.name}</b><br>Qtd: %{y:,.0f}<extra></extra>'
    ))

fig.update_layout(
    barmode='group',
    hovermode='closest',
    margin=dict(l=40, r=20, t=30, b=60),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    yaxis=dict(showgrid=True, gridcolor='#E0E6ED', title='Quantidade Comercializada'),
    xaxis=dict(type='category', title='Mês / Ano de Referência'),
    legend=dict(orientation='h', y=1.18, x=0),
    font=dict(family="Segoe UI", color='#6C757D')
)

chart_html = fig.to_html(full_html=False, include_plotlyjs=False, div_id="plotlyChart")

dados_json_str = df.to_json(orient='records')
mapa_cores_json = json.dumps(mapa_cores_segmentos)

# -------------------------------------------------------------
# 7. HTML TEMPLATE + JS
# -------------------------------------------------------------
html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Consórcios</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

    <style>
        :root {{
            --primary-red: #FF0000;
            --secondary-blue: #424242;
            --accent-gray: #595858;
            --bg-light: #FFFFFF;
            --card-bg: #fcfafa;
            --border-color: #E0E6ED;
        }}
        body {{
            background-color: var(--bg-light);
            color: #333;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .text-gray {{ color: var(--accent-gray); font-weight: 700; }}
        .kpi-card {{
            border: none;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(10, 37, 64, 0.05);
            background-color: var(--card-bg);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            cursor: help;
        }}
        .kpi-card-primary {{
            background-color: var(--primary-red);
            color: #FFFFFF;
        }}
        .kpi-title {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            opacity: 0.85;
            font-weight: 600;
        }}
        .kpi-value {{
            font-size: 1.35rem;
            font-weight: 700;
        }}
        .kpi-value-segmento {{
            font-size: 1.20rem;
        }}
        .chart-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            height: 520px;
            display: flex;
            flex-direction: column;
        }}
        .chart-scroll-container {{
            flex: 1;
            overflow-y: auto;
            overflow-x: hidden;
        }}
        .filter-section {{
            background-color: var(--card-bg);
            border-radius: 10px;
            padding: 1rem 1.5rem;
            border: 1px solid var(--card-bg);
            margin-bottom: 1.5rem;
        }}
        .admin-list .list-group-item:hover {{
            background-color: #f8f9fa;
        }}
        .col-kpi {{
            flex: 0 0 auto;
            width: 20%;
        }}
        @media (max-width: 991px) {{
            .col-kpi {{
                width: 50%;
            }}
        }}
        @media (max-width: 575px) {{
            .col-kpi {{
                width: 100%;
            }}
        }}
    </style>
</head>
<body class="p-4">

    <div class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-4 pb-2 border-bottom">
            <h2><span class="text-gray">CONCEPT</span></h2>
            <span class="text-muted">Dados recuperados via Python</span>
        </div>

        <!-- FILTROS -->
        <div class="filter-section shadow-sm">
            <div class="row align-items-end g-3">
                <div class="col-md-4">
                    <label for="selectSegmento" class="form-label fw-bold">Segmento:</label>
                    <select id="selectSegmento" class="form-select" onchange="aplicarFiltros()">
                        <option value="TODOS">Todos os Segmentos ({len(variavel_segmentos)})</option>
                        {"".join([f'<option value="{s}">{s}</option>' for s in variavel_segmentos])}
                    </select>
                </div>
                <div class="col-md-5">
                    <label for="selectAdmin" class="form-label fw-bold">Administradora:</label>
                    <select id="selectAdmin" class="form-select" onchange="aplicarFiltros()">
                        <option value="TODOS">Todas as Administradoras ({len(variavel_administradoras)})</option>
                        {"".join([f'<option value="{a}">{a}</option>' for a in variavel_administradoras])}
                    </select>
                </div>
                <div class="col-md-3">
                    <button class="btn btn-primary w-100 fw-bold" onclick="resetarFiltros()" style="background-color: var(--accent-gray); border-color: var(--accent-gray);">
                        Filtro Geral (Limpar)
                    </button>
                </div>
            </div>
        </div>

        <!-- KPIS -->
        <div class="row mb-4 g-3">
            
            <div class="col-kpi">
                <div class="card kpi-card border h-100">
                    <div class="card-body">
                        <div class="kpi-title text-muted">Melhor Segmento (Geral)</div>
                        <div class="kpi-value kpi-value-segmento text-truncate" style="color: var(--secondary-blue);" id="kpiMelhorSegmento" title="{melhor_seg_global_texto}">{melhor_seg_global_texto}</div>
                        <small class="text-muted">Campeão da base (Fixo)</small>
                    </div>
                </div>
            </div>

            <div class="col-kpi">
                <div class="card kpi-card border h-100">
                    <div class="card-body">
                        <div class="kpi-title text-muted">Melhor Mês da Série</div>
                        <div class="kpi-value" style="color: var(--secondary-blue);" id="kpiMelhorMes">0</div>
                        <small class="text-muted">Mês com pico de vendas</small>
                    </div>
                </div>
            </div>

            <div class="col-kpi">
                <div class="card kpi-card border h-100">
                    <div class="card-body">
                        <div class="kpi-title text-muted">Média por Operação</div>
                        <div class="kpi-value" style="color: var(--secondary-blue);" id="kpiMedia">0</div>
                        <small class="text-muted">Média por registro exibido</small>
                    </div>
                </div>
            </div>
            
            <div class="col-kpi">
                <div class="card kpi-card border h-100">
                    <div class="card-body">
                        <div class="kpi-title text-muted">Qtd de Clientes / Registros</div>
                        <div class="kpi-value text-dark" id="kpiTotalClientes">0</div>
                        <small class="text-muted">Total da amostra exibida</small>
                    </div>
                </div>
            </div>
            <div class="col-kpi">
                <div class="card kpi-card kpi-card-primary h-100">
                    <div class="card-body">
                        <div class="kpi-title">Qtd Total Comercializada</div>
                        <div class="kpi-value" id="kpiTotalQtd">0</div>
                        <small class="opacity-75">Período: {dataInicio} - {dataFim}</small>
                    </div>
                </div>
            </div>
        </div>

        <!-- COLUNA 3 PARA LISTA DE ADMIN (ESTÁTICA) / COLUNA 9 PARA SEGMENTOS -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="chart-card">
                    <h5 class="mb-3" style="color: var(--primary-red); font-size: 1rem;">Administradoras Faturamento</h5>
                    <div class="chart-scroll-container">
                        <ul class="list-group list-group-flush admin-list">
                            {lista_admin_html}
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-9">
                <div class="chart-card">
                    <h5 class="mb-3" style="color: var(--primary-red);">Evolução Mensal por Segmento</h5>
                    <div class="chart-scroll-container">
                        {chart_html}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const rawData = {dados_json_str};
        const mapCoresSegmentos = {mapa_cores_json};

        function aplicarFiltros() {{
            const segSelecionado = document.getElementById("selectSegmento").value;
            const adminSelecionada = document.getElementById("selectAdmin").value;

            let dadosFiltrados = rawData.filter(item => {{
                let matchSeg = (segSelecionado === "TODOS" || item.segmento === segSelecionado);
                let matchAdmin = (adminSelecionada === "TODOS" || item.administradora === adminSelecionada);
                return matchSeg && matchAdmin;
            }});

            atualizarKPIs(dadosFiltrados);
            atualizarGraficoPorSegmento(dadosFiltrados);
        }}

        function resetarFiltros() {{
            document.getElementById("selectSegmento").value = "TODOS";
            document.getElementById("selectAdmin").value = "TODOS";
            aplicarFiltros();
        }}

        function atualizarKPIs(dados) {{
            let totalQtd = dados.reduce((acc, curr) => acc + (parseInt(curr.quantidade) || 0), 0);
            let totalClientes = dados.length;
            let media = totalClientes > 0 ? (totalQtd / totalClientes).toFixed(1) : 0;

            let somaPorMes = {{}};

            dados.forEach(item => {{
                let mes = item.data_referencia;
                let qtd = parseInt(item.quantidade) || 0;

                if (mes && mes !== 'Indefinido') {{
                    somaPorMes[mes] = (somaPorMes[mes] || 0) + qtd;
                }}
            }});

            // Melhor Mês (Reativo ao filtro)
            let melhorMes = "N/A";
            let maiorValorMes = -1;
            Object.keys(somaPorMes).forEach(mes => {{
                if (somaPorMes[mes] > maiorValorMes) {{
                    maiorValorMes = somaPorMes[mes];
                    melhorMes = mes;
                }}
            }});

            let textoMelhorMes = maiorValorMes > 0 ? `${{melhorMes}} (${{maiorValorMes.toLocaleString('pt-BR')}})` : "N/A";

            // NOTA: O KPI "Melhor Segmento (Geral)" permanece estático conforme preenchido pelo Python

            document.getElementById("kpiTotalQtd").innerText = totalQtd.toLocaleString('pt-BR');
            document.getElementById("kpiTotalClientes").innerText = totalClientes.toLocaleString('pt-BR');
            document.getElementById("kpiMelhorMes").innerText = textoMelhorMes;
            document.getElementById("kpiMedia").innerText = media.replace('.', ',');
        }}

        function atualizarGraficoPorSegmento(dados) {{
            let conjuntoSegmentos = new Set();
            dados.forEach(item => {{
                if(item.segmento) conjuntoSegmentos.add(item.segmento);
            }});
            let segmentos = Array.from(conjuntoSegmentos).sort();

            let conjuntoMeses = new Set();
            dados.forEach(item => {{
                if(item.data_referencia && item.data_referencia !== 'Indefinido') {{
                    conjuntoMeses.add(item.data_referencia);
                }}
            }});

            let meses = Array.from(conjuntoMeses).sort((a, b) => {{
                let [mesA, anoA] = a.split('/').map(Number);
                let [mesB, anoB] = b.split('/').map(Number);
                return new Date(anoA, mesA - 1) - new Date(anoB, mesB - 1);
            }});

            let dadosAgrupados = {{}};
            segmentos.forEach(seg => {{
                dadosAgrupados[seg] = {{}};
                meses.forEach(mes => {{ dadosAgrupados[seg][mes] = 0; }});
            }});

            dados.forEach(item => {{
                let seg = item.segmento;
                let mes = item.data_referencia;
                if(dadosAgrupados[seg] && dadosAgrupados[seg][mes] !== undefined) {{
                    dadosAgrupados[seg][mes] += parseInt(item.quantidade || 0);
                }}
            }});

            let traces = segmentos.map(seg => {{
                let valores = meses.map(m => dadosAgrupados[seg][m]);
                return {{
                    x: meses,
                    y: valores,
                    name: seg,
                    type: 'bar',
                    marker: {{ color: mapCoresSegmentos[seg] || '#1A4B83' }},
                    text: valores.map(v => v > 0 ? v.toLocaleString('pt-BR') : ''),
                    textposition: 'outside',
                    hovertemplate: '<b>%{{fullData.name}}</b><br>Qtd: %{{y:,.0f}}<extra></extra>'
                }};
            }});

            let layout = {{
                barmode: 'group',
                hovermode: 'closest',
                margin: {{ l: 40, r: 20, t: 30, b: 60 }},
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                yaxis: {{ showgrid: true, gridcolor: '#E0E6ED', title: 'Quantidade Comercializada' }},
                xaxis: {{ type: 'category', title: 'Mês / Ano de Referência' }},
                legend: {{ orientation: 'h', y: 1.18, x: 0 }},
                font: {{ family: "Segoe UI", color: '#6C757D' }}
            }};

            Plotly.react('plotlyChart', traces, layout);
        }}

        document.addEventListener("DOMContentLoaded", function() {{
            aplicarFiltros();
        }});
    </script>
</body>
</html>
"""

# 8. Salva o HTML gerado
with open("dashboard_consorcios.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("Dashboard gerado com sucesso!")
