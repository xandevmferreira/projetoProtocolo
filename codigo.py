import sqlite3
from flask import Flask, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dash import Dash, html, dcc, Input, Output, State, no_update, dash_table, clientside_callback, callback_context
from datetime import datetime
import time

item_style = {'marginTop': '10px', 'fontWeight': 'bold'}

# Crie o Flask server e configure a chave secreta
server = Flask(__name__)
server.secret_key = "chave_super_secreta"

# Configure o Flask-Login
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = "/login"  # Rota de login

# Crie o Dash app, passando o server Flask
app = Dash(__name__, server=server, suppress_callback_exceptions=True)

# Modelo de usuário para Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('protocolo.db')
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM usuarios WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None

# Função para inicializar o banco de dados (incluindo usuários)
def init_db():
    conn = sqlite3.connect('protocolo.db')
    c = conn.cursor()
    # Tabela para cadastro de protocolos
    c.execute('''
        CREATE TABLE IF NOT EXISTS protocolo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    ''')
    # Tabela para os dados do formulário
    c.execute('''
        CREATE TABLE IF NOT EXISTS formulario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT,
            caso TEXT,
            descricao_peca TEXT,
            data_distribuicao TEXT,
            PAE TEXT,
            prioridade TEXT,
            data_prazo TEXT,
            responsavel TEXT,
            cor TEXT
        )
    ''')
    # Tabela de usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    # Insere usuário padrão se não existir
    c.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (username, password, role) VALUES ('admin', '1234', 'admin')")
    conn.commit()
    conn.close()

init_db()

# Função para buscar os protocolos
def get_protocolos():
    conn = sqlite3.connect('protocolo.db')
    c = conn.cursor()
    c.execute("SELECT nome FROM protocolo")
    protocolos = c.fetchall()
    conn.close()
    return [{"label": p[0], "value": p[0]} for p in protocolos]

# Layout da tela de login
layout_login = html.Div([
    html.H2("Login", style={'textAlign': 'center'}),
    dcc.Input(id='login-username', type='text', placeholder='Usuário', style={'margin': '10px'}),
    dcc.Input(id='login-password', type='password', placeholder='Senha', style={'margin': '10px'}),
    html.Button('Entrar', id='login-button', n_clicks=0),
    html.Div(id='login-message', style={'color': 'red', 'marginTop': '10px'})
], style={'padding': '20px', 'textAlign': 'center'})

# Layout de visualização dos registros com caixa de busca e botão Finalizar
layout_visualizacao = html.Div([
    html.H3("Visualização dos Registros"),
    dcc.Input(
        id="buscar-protocolo",
        type="text",
        placeholder="Buscar por protocolo",
        style={'width': '50%', 'marginBottom': '20px'}
    ),
    html.Button('Buscar', id='buscar-button', n_clicks=0),
    html.Div(id="buscar-message", style={'color': 'red', 'marginBottom': '20px'}),
    dcc.Dropdown(
        id="filtro_protocolo",
        options=get_protocolos(),
        placeholder="Filtrar por protocolo",
        style={'width': '50%', 'marginTop': '20px'}
    ),
    html.Button('Atualizar', id='atualizar-dados', n_clicks=0),
    html.Br(),
    # DataTable com row selection e estilo condicional para a coluna "cor"
    dash_table.DataTable(
        id='tabela-dados',
        columns=[
            {"name": "ID", "id": "id"},
            {"name": "Protocolo", "id": "protocolo"},
            {"name": "Caso", "id": "caso"},
            {"name": "Descrição", "id": "descricao_peca"},
            {"name": "Distribuição", "id": "data_distribuicao"},
            {"name": "PAE", "id": "PAE"},
            {"name": "Prioridade", "id": "prioridade"},
            {"name": "Prazo", "id": "data_prazo"},
            {"name": "Responsável", "id": "responsavel"},
            {"name": "Cor", "id": "cor"}
        ],
        page_size=10,
        row_selectable="single",
        selected_rows=[],
        style_table={'overflowX': 'auto'},
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{cor} = "green"',
                    'column_id': 'cor'
                },
                'backgroundColor': 'green',
                'color': 'transparent'
            },
            {
                'if': {
                    'filter_query': '{cor} = "amarela"',
                    'column_id': 'cor'
                },
                'backgroundColor': 'yellow',
                'color': 'transparent'
            },
            {
                'if': {
                    'filter_query': '{cor} = "vermelha"',
                    'column_id': 'cor'
                },
                'backgroundColor': 'red',
                'color': 'transparent'
            }
        ]
    ),
    html.Br(),
    html.Button("Finalizar Protocolo", id="finalizar-button", n_clicks=0),
    html.Br(),
    dcc.Link("Voltar", href="/")
], style={'padding': '20px'})

# Layout de cadastro de protocolos
layout_cadastro = html.Div([
    html.H3("Novo Cadastro de Protocolo"),
    dcc.Input(
        id='novo-protocolo',
        placeholder='Número de protocolo',
        style={'margin-right': '10px', 'width': '100%'}
    ),
    html.Button('Adicionar Protocolo', id='adicionar-protocolo', n_clicks=0),
    html.Div(id='mensagem-protocolo', style={'margin-top': '10px'}),
    html.Br(),
    dcc.Link("Ir para Formulário de Cadastro", href="/formulario")
], style={'padding': '20px'})

# Layout do formulário de cadastro (alinhar à esquerda)
layout_formulario = html.Div([
    html.H3("Formulário de Cadastro", id="titulo-formulario"),
    html.Div([
        html.Div([
            html.Label('Protocolo', style=item_style),
            dcc.Dropdown(
                id='protocolo',
                placeholder="Selecione o protocolo",
                options=get_protocolos(),
                style={'width': '100%'}
            )
        ]),
        html.Div([
            html.Label('Caso', style=item_style),
            dcc.Input(
                id='caso',
                type='number',
                placeholder='Digite o número do caso',
                style={'width': '100%'}
            )
        ]),
        html.Div([
            html.Label('Descrição da peça', style=item_style),
            dcc.Input(
                id='descricao_peca',
                type='text',
                placeholder='Digite a descrição da peça',
                style={'width': '100%'}
            )
        ]),
        html.Div([
            html.Label('Data da distribuição', style=item_style),
            dcc.DatePickerSingle(
                id='data_distribuicao',
                placeholder="Selecione a data",
                display_format='DD/MM/YYYY',
                month_format='MMMM YYYY',
                first_day_of_week=1,
                style={'width': '100%'}
            )
        ]),
        html.Div([
            html.Label('PAE', style=item_style),
            dcc.RadioItems(
                id='pae',
                options=[{'label': 'Sim', 'value': 'Sim'}, {'label': 'Não', 'value': 'Não'}],
                value=None,
                labelStyle={'display': 'block'}
            )
        ]),
        html.Div([
            html.Label('Prioridade', style=item_style),
            dcc.RadioItems(
                id='prioridade',
                options=[
                    {'label': 'Baixa', 'value': 'Baixa'},
                    {'label': 'Média', 'value': 'Média'},
                    {'label': 'Alta', 'value': 'Alta'}
                ],
                value=None,
                labelStyle={'display': 'block'}
            )
        ]),
        html.Div([
            html.Label('Data prazo', style=item_style),
            dcc.DatePickerSingle(
                id='data_prazo',
                placeholder="Selecione a data",
                display_format='DD/MM/YYYY',
                month_format='MMMM YYYY',
                first_day_of_week=1,
                style={'width': '100%'}
            )
        ]),
        html.Div([
            html.Label('Responsável', style=item_style),
            dcc.Input(
                id='responsavel',
                type='text',
                placeholder='Digite o nome do responsável',
                style={'width': '100%'}
            )
        ]),
        html.Div([
            html.Label('Observações', style=item_style),
            dcc.Input(
                id='observacoes',
                type='text',
                placeholder='Digite qualquer observação',
                style={'width': '100%'}
            )
        ])
    ], style={'width': '60%', 'margin': '0', 'border': '1px solid #ccc', 'padding': '20px', 'borderRadius': '5px'}),
    html.Br(),
    html.Button('Salvar', id='salvar-button', n_clicks=0,
                style={'width': '30%', 'margin': '0 auto', 'display': 'block'}),
    html.Div(id='mensagem', style={'padding': '10px', 'textAlign': 'center'}),
    html.Br(),
    dcc.Link("Voltar", href="/cadastro")
], style={'padding': '20px', 'textAlign': 'left'})

# Layout de gerenciamento de usuários (somente admin)
layout_usuarios = html.Div([
    html.H3("Gerenciamento de Usuários"),
    dcc.Input(id='novo-username', type='text', placeholder='Novo Usuário', style={'margin': '10px'}),
    dcc.Input(id='novo-password', type='password', placeholder='Senha', style={'margin': '10px'}),
    dcc.Dropdown(
         id='novo-role',
         options=[{'label': 'admin', 'value': 'admin'}, {'label': 'user', 'value': 'user'}],
         placeholder="Selecione a permissão",
         style={'width': '50%', 'margin': '10px'}
    ),
    html.Button('Criar Usuário', id='criar-usuario-button', n_clicks=0),
    html.Div(id='mensagem-usuario', style={'color': 'green', 'marginTop': '10px'}),
    dcc.Link("Voltar", href="/")
], style={'padding': '20px', 'textAlign': 'center'})

# Layout principal
app.layout = html.Div([
    dcc.Store(id="store-protocolos", data=get_protocolos()),
    dcc.Location(id="url", refresh=False),
    dcc.Store(id='last-activity', storage_type='session'),
    dcc.Interval(id='logout-check-interval', interval=60*1000),
    html.Div(id='activity-tracker', n_clicks=0, style={'display': 'none'}),

    # Botão para Dark Mode e Logout
    html.Div([
        dcc.Checklist(
            id='dark-mode',
            options=[{'label': 'Dark Mode', 'value': 'dark'}],
            value=[],
            inline=True
        ),
        html.Button("Logout", id="logout-button", n_clicks=0,
                   style={'position': 'absolute', 'right': '10px', 'top': '10px'})
    ], style={'position': 'relative', 'textAlign': 'center', 'margin': '10px'}),

    # Links de navegação (incluindo Gerenciar Usuários para admin)
    html.Div([
        dcc.Link("Cadastro de Protocolo", href="/cadastro"),
        html.Br(),
        dcc.Link("Formulário de Cadastro", href="/formulario"),
        html.Br(),
        dcc.Link("Visualizar Registros", href="/visualizacao"),
        html.Br(),
        dcc.Link("Gerenciar Usuários", href="/usuarios")
    ], style={'padding': '10px', 'textAlign': 'center'}),

    html.Div(id="page-content"),
    html.Div([
        html.Div("Sistema de cadastro de protocolos", style={'fontWeight': 'bold'}),
        html.Img(src=app.get_asset_url('PCEPA.jfif'), style={'height': '60px', 'marginLeft': '15px'})
    ], style={'position': 'fixed', 'bottom': '0', 'width': '100%', 'backgroundColor': '#f1f1f1', 'textAlign': 'center', 'padding': '10px', 'boxShadow': '0 -2px 5px rgba(0,0,0,0.1)'})
], id="main-container", style={'backgroundColor': '#ADD8E6', 'minHeight': '100vh'})

# Callback para rastrear atividade do usuário (clientside)
clientside_callback(
    """
    function() {
        window.addEventListener('mousemove', function() {
            document.getElementById('activity-tracker').click();
        });
        window.addEventListener('keydown', function() {
            document.getElementById('activity-tracker').click();
        });
        return '';
    }
    """,
    Output('activity-tracker', 'children'),
    Input('activity-tracker', 'children')
)

# Callback de login
@app.callback(
    Output('login-message', 'children'),
    Input('login-button', 'n_clicks'),
    [State('login-username', 'value'),
     State('login-password', 'value')],
    prevent_initial_call=True
)
def login(n_clicks, username, password):
    if n_clicks > 0:
        conn = sqlite3.connect('protocolo.db')
        c = conn.cursor()
        c.execute("SELECT id, username, role FROM usuarios WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            login_user(User(user[0], user[1], user[2]))
            return dcc.Location(pathname='/', id='url-redirect')
        return "Credenciais inválidas! Tente novamente."
    return no_update

# Callback para criar novos usuários (somente admin)
@app.callback(
    Output('mensagem-usuario', 'children'),
    Input('criar-usuario-button', 'n_clicks'),
    [State('novo-username', 'value'),
     State('novo-password', 'value'),
     State('novo-role', 'value')],
    prevent_initial_call=True
)
def criar_usuario(n_clicks, novo_username, novo_password, novo_role):
    if n_clicks > 0:
        if not novo_username or not novo_password or not novo_role:
            return "Preencha todos os campos."
        try:
            conn = sqlite3.connect('protocolo.db')
            c = conn.cursor()
            c.execute("INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)", (novo_username, novo_password, novo_role))
            conn.commit()
            conn.close()
            return f"Usuário {novo_username} criado com sucesso!"
        except sqlite3.IntegrityError:
            return "Usuário já existe!"
    return no_update

# Atualiza o timestamp da última atividade
@app.callback(
    Output('last-activity', 'data'),
    Input('activity-tracker', 'n_clicks'),
    prevent_initial_call=True
)
def update_last_activity(_):
    return time.time()

# Verifica inatividade e faz logout
@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("logout-button", "n_clicks"),
    prevent_initial_call=True
)
def logout(n_clicks):
    if n_clicks > 0:
        logout_user()
        return "/login"
    return no_update

@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('logout-check-interval', 'n_intervals'),
    State('last-activity', 'data'),
    prevent_initial_call=True
)
def check_logout(_, last_activity):
    if last_activity and (time.time() - last_activity) > 600:
        logout_user()
        return "/login"
    return no_update

# Callback principal de controle de acesso
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    if not current_user.is_authenticated:
        if pathname != "/login":
            return layout_login
        return layout_login
    if pathname == "/logout":
        return no_update
    if pathname == "/formulario":
        return layout_formulario
    elif pathname == "/visualizacao":
        return layout_visualizacao
    elif pathname == "/cadastro":
        return layout_cadastro
    elif pathname == "/usuarios":
        if current_user.role == 'admin':
            return layout_usuarios
        else:
            return html.Div("Acesso negado", style={'padding': '20px', 'textAlign': 'center'})
    return layout_cadastro

# Callback para atualizar o título do formulário conforme Dark Mode
@app.callback(
    Output("titulo-formulario", "style"),
    Input("dark-mode", "value")
)
def atualizar_titulo(dark):
    if dark and 'dark' in dark:
        return {'color': 'white'}
    else:
        return {'color': 'black'}

# Callback único para atualizar as opções do dropdown de protocolos,
# combinando os dados do armazenamento e a busca,
# e exibindo mensagem se nenhum protocolo for encontrado.
@app.callback(
    [Output("filtro_protocolo", "options"),
     Output("buscar-message", "children")],
    [Input("store-protocolos", "data"),
     Input('buscar-button', 'n_clicks')],
    State('buscar-protocolo', 'value'),
    prevent_initial_call=True,
    allow_duplicate=True
)
def atualizar_filtro_com_busca(store_data, n_clicks, search_text):
    if search_text and n_clicks > 0:
        filtered_protocolos = [p for p in store_data if search_text.lower() in p['label'].lower()]
        if not filtered_protocolos:
            return [], "Protocolo não consta"
        return filtered_protocolos, ""
    return store_data, ""

# Callback para adicionar protocolo (no cadastro de protocolos)
@app.callback(
    [Output('mensagem-protocolo', 'children'),
     Output('novo-protocolo', 'value'),
     Output('store-protocolos', 'data')],
    Input('adicionar-protocolo', 'n_clicks'),
    State('novo-protocolo', 'value')
)
def adicionar_protocolo(n_clicks, nome):
    if n_clicks == 0:
        return no_update, no_update, no_update
    if not nome:
        return "Insira um nome válido!", "", no_update
    try:
        conn = sqlite3.connect('protocolo.db')
        c = conn.cursor()
        c.execute("INSERT INTO protocolo (nome) VALUES (?)", (nome,))
        conn.commit()
        return f"Protocolo {nome} cadastrado!", "", get_protocolos()
    except sqlite3.IntegrityError:
        return "Protocolo já existe!", "", no_update
    finally:
        conn.close()

@app.callback(
    Output("protocolo", "options"),
    Input("store-protocolos", "data")
)
def atualizar_dropdown(data):
    return data if data else []

# Callback para salvar os dados do formulário
@app.callback(
    [Output('mensagem', 'children'),
     Output('protocolo', 'value'),
     Output('caso', 'value'),
     Output('descricao_peca', 'value'),
     Output('data_distribuicao', 'date'),
     Output('pae', 'value'),
     Output('prioridade', 'value'),
     Output('data_prazo', 'date'),
     Output('responsavel', 'value'),
     Output('observacoes', 'value')],
    Input('salvar-button', 'n_clicks'),
    [State('protocolo', 'value'),
     State('caso', 'value'),
     State('descricao_peca', 'value'),
     State('data_distribuicao', 'date'),
     State('pae', 'value'),
     State('prioridade', 'value'),
     State('data_prazo', 'date'),
     State('responsavel', 'value'),
     State('observacoes', 'value')]
)
def salvar_formulario(n_clicks, protocolo, caso, descricao_peca, data_distribuicao,
                      pae, prioridade, data_prazo, responsavel, cor):
    if n_clicks == 0:
        return (no_update,)*10
    try:
        conn = sqlite3.connect('protocolo.db')
        cursor = conn.cursor()
        # Se o usuário não for admin, forçamos que o responsável seja o seu nome
        if current_user.role != 'admin':
            responsavel = current_user.username
        cursor.execute('''
            INSERT INTO formulario VALUES (
                NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        ''', (
            protocolo,
            caso,
            descricao_peca,
            data_distribuicao,
            pae,
            prioridade,
            data_prazo,
            responsavel,
            cor
        ))
        conn.commit()
        conn.close()
        return ("Dados salvos com sucesso!", None, None, "", None, None, None, None, "", "")
    except sqlite3.Error as e:
        return (f"Erro ao salvar dados: {str(e)}",
                protocolo,
                caso,
                descricao_peca,
                data_distribuicao,
                pae,
                prioridade,
                data_prazo,
                responsavel,
                cor)

# Callback para carregar os dados na tabela de registros,
# utilizando callback_context para detectar o botão acionado e aplicando controle de acesso,
# além de calcular a cor com base na data prazo:
@app.callback(
    Output("tabela-dados", "data"),
    [Input("atualizar-dados", "n_clicks"),
     Input("buscar-button", "n_clicks")],
    [State("filtro_protocolo", "value"),
     State("buscar-protocolo", "value")],
    prevent_initial_call=True
)
def carregar_dados(n_atualizar, n_buscar, filtro_value, buscar_value):
    ctx = callback_context
    if not ctx.triggered:
        raise Exception("No trigger")
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    conn = sqlite3.connect('protocolo.db')
    c = conn.cursor()
    # Se o usuário for admin, ele pode ver todos os registros
    if current_user.role == 'admin':
        if trigger_id == "buscar-button" and buscar_value:
            c.execute("SELECT * FROM formulario WHERE protocolo LIKE ?", ('%' + buscar_value + '%',))
        elif filtro_value:
            c.execute("SELECT * FROM formulario WHERE protocolo = ?", (filtro_value,))
        else:
            c.execute("SELECT * FROM formulario")
    else:
        # Usuários com role 'user' só veem registros onde o responsável é o seu nome
        user_name = current_user.username
        if trigger_id == "buscar-button" and buscar_value:
            c.execute("SELECT * FROM formulario WHERE responsavel = ? AND responsavel LIKE ?", (user_name, '%' + buscar_value + '%'))
        else:
            c.execute("SELECT * FROM formulario WHERE responsavel = ?", (user_name,))
    rows = c.fetchall()
    conn.close()
    # Para cada registro, se não estiver finalizado (cor != 'green'), calcular a cor com base na data prazo
    tabela = []
    for row in rows:
        record = list(row)
        # record[7] é data_prazo e record[9] é cor
        if record[9] != "green" and record[7]:
            try:
                prazo = datetime.strptime(record[7], "%d/%m/%Y")
                dias_restantes = (prazo - datetime.now()).days
                if 8 <= dias_restantes <= 15:
                    record[9] = "amarela"
                elif dias_restantes <= 7:
                    record[9] = "vermelha"
                else:
                    record[9] = ""
            except Exception as e:
                record[9] = ""
        tabela.append({
            "id": record[0],
            "protocolo": record[1],
            "caso": record[2],
            "descricao_peca": record[3],
            "data_distribuicao": record[4],
            "PAE": record[5],
            "prioridade": record[6],
            "data_prazo": record[7],
            "responsavel": record[8],
            "cor": record[9]
        })
    return tabela

# Callback para finalizar protocolo (atualiza a cor para green)
@app.callback(
    Output("tabela-dados", "data", allow_duplicate=True),
    Input("finalizar-button", "n_clicks"),
    State("tabela-dados", "derived_virtual_data"),
    State("tabela-dados", "selected_rows"),
    prevent_initial_call=True
)
def finalizar_protocolo(n_clicks, table_data, selected_rows):
    if n_clicks > 0 and selected_rows is not None and len(selected_rows) > 0:
        selected_index = selected_rows[0]
        record = table_data[selected_index]
        protocolo_id = record["id"]
        conn = sqlite3.connect('protocolo.db')
        c = conn.cursor()
        # Atualiza o campo cor para green no registro selecionado
        c.execute("UPDATE formulario SET cor = ? WHERE id = ?", ("green", protocolo_id))
        conn.commit()
        conn.close()
        # Após a atualização, recarrega os dados
        return carregar_dados(1, 0, None, None)
    return no_update

@app.callback(
    Output("main-container", "style"),
    Input("dark-mode", "value")
)
def tema_escuro(modo):
    if 'dark' in modo:
        return {'backgroundColor': '#2c2c2c', 'minHeight': '100vh'}
    else:
        return {'backgroundColor': '#ADD8E6', 'minHeight': '100vh'}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8050, debug=True)
