import sqlite3
import dash                             
from flask import Flask, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dash import Dash, html, dcc, Input, Output, State, no_update, dash_table, clientside_callback, callback_context
from datetime import datetime
import time
app = Dash(__name__, suppress_callback_exceptions=True)

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
    return User(user[0], user[1], user[2]) if user else None



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

#Função auxiliar nas buscas de usuário no DB.

def get_usuarios():
    conn = sqlite3.connect('protocolo.db')
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM usuarios")
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "username": r[1], "role": r[2]}
        for r in rows
    ]

# Função para buscar os protocolos
def get_protocolos():
    conn = sqlite3.connect('protocolo.db')
    c = conn.cursor()
    c.execute("SELECT nome FROM protocolo")
    protocolos = c.fetchall()
    conn.close()
    return [{"label": p[0], "value": p[0]} for p in protocolos]

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
        style={'width': '20%', 'marginBottom': '20px'}
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

# 3) Layout de gerenciamento de usuários (agora contendo cadastro, edição E deleção)
layout_usuarios = html.Div([
    html.H3("Gerenciamento de Usuários"),

    # cadastro
    html.Div([
        dcc.Input(id='novo-username', placeholder='Novo Usuário', style={'margin': '5px'}),
        dcc.Input(id='novo-password', type='password', placeholder='Senha', style={'margin': '5px'}),
        dcc.Dropdown(
            id='novo-role',
            options=[{'label': 'admin', 'value': 'admin'},
                     {'label': 'user',  'value': 'user'}],
            placeholder="Selecione a permissão",
            style={'width': '200px', 'margin': '5px'}
        ),
        html.Button('Criar Usuário', id='cadastrar-usuario-button', n_clicks=0, style={'margin': '5px'})
    ], style={'borderBottom': '1px solid #ccc', 'paddingBottom': '1rem'}),

    # edição
    html.Div([
        dcc.Input(id='edit-user-id', type='number', placeholder='ID p/ Editar', style={'margin': '5px'}),
        dcc.Input(id='edit-username', placeholder='Novo Username', style={'margin': '5px'}),
        dcc.Input(id='edit-password', type='password', placeholder='Nova Senha', style={'margin': '5px'}),
        dcc.Dropdown(
            id='edit-role',
            options=[{'label': 'admin', 'value': 'admin'},
                     {'label': 'user',  'value': 'user'}],
            placeholder="Novo Role",
            style={'width': '200px', 'margin': '5px'}
        ),
        html.Button('Atualizar Usuário', id='atualizar-usuario-button', n_clicks=0, style={'margin': '5px'})
    ], style={'borderBottom': '1px solid #ccc', 'paddingBottom': '1rem'}),

    # deleção
    html.Div([
        dcc.Input(id='delete-user-id', type='number', placeholder='ID p/ Deletar', style={'margin': '5px'}),
        html.Button('Deletar Usuário', id='deletar-usuario-button', n_clicks=0,
                    style={'margin': '5px', 'backgroundColor': '#d9534f', 'color': 'white'})
    ], style={'marginBottom': '2rem'}),

    # feedback e tabela já populada
    html.Div(id='mensagem-gerenciamento', style={'marginBottom': '1rem'}),
    dash_table.DataTable(
        id='tabela-usuarios',
        columns=[
            {'name': 'ID',       'id': 'id'},
            {'name': 'Usuário',  'id': 'username'},
            {'name': 'Função',   'id': 'role'}
        ],
        data=get_usuarios(),   # carrega os usuários já existentes
        page_size=10
    )
], style={'padding': '20px'})


html.Button('Atualizar', id='atualizar-dados', n_clicks=0),
html.Br(),
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
                'color': 'rgba(0,0,0,0)'
            },
            {
                'if': {
                    'filter_query': '{cor} = "amarela"',
                    'column_id': 'cor'
                },
                'backgroundColor': 'yellow',
                'color': 'rgba(0,0,0,0)'
            },
            {
                'if': {
                    'filter_query': '{cor} = "vermelha"',
                    'column_id': 'cor'
                },
                'backgroundColor': 'red',
                'color': 'rgba(0,0,0,0)'
            }
        ]
    ),
html.Br(),
html.Button("Finalizar Protocolo", id="finalizar-button", n_clicks=0),
html.Button("Deletar Protocolo", id="deletar-protocolo-button", n_clicks=0,
            style={'marginLeft': '10px', 'backgroundColor': '#d9534f', 'color': 'white'}),
html.Div(id="mensagem-deletar", style={'color': 'red', 'marginTop': '10px'}),
html.Br(),
dcc.Link("Voltar", href="/")

@app.callback(
    [Output("tabela-dados", "data", allow_duplicate=True),
    Output("mensagem-deletar", "children")],
    Input("deletar-protocolo-button", "n_clicks"),
    State("tabela-dados", "derived_virtual_data"),
    State("tabela-dados", "selected_rows"),
    prevent_initial_call=True
)
def deletar_protocolo(n_clicks, table_data, selected_rows):
    if n_clicks and selected_rows:
        idx = selected_rows[0]
        record = table_data[idx]
        protocolo_id = record["id"]
        try:
            conn = sqlite3.connect('protocolo.db')
            c = conn.cursor()
            # Se quiser deletar o registro do formulário:
            c.execute("DELETE FROM formulario WHERE id = ?", (protocolo_id,))
            conn.commit()
            conn.close()
            # Depois recarrega a tabela
            novos = carregar_dados(1, 0, None, None)
            return novos, "Protocolo deletado com sucesso."
        except Exception as e:
            return no_update, f"Erro ao deletar: {e}"
    return no_update, ""


# Layout de cadastro de protocolos
layout_cadastro = html.Div([
    html.H3("Novo Cadastro de Protocolo"),
    dcc.Input(
        id='novo-protocolo',
        placeholder='Número de protocolo',
        style={'margin-right': '10px', 'width': '20%'}
    ),
    html.Button('Adicionar Protocolo', id='adicionar-protocolo', n_clicks=0),
    html.Div(id='mensagem-protocolo', style={'margin-top': '10px'}),
    html.Br(),
    dcc.Link("Ir para Formulário de Cadastro", href="/formulario")
], style={'padding': '20px'})


# Layout do formulário de cadastro (alinhar à esquerda)
layout_formulario = html.Div([
    html.H3(
    "Formulário de Cadastro", 
    id="titulo-formulario", 
    style={
        'textAlign': 'center',
        'marginBottom': '30px',
        'width': '100%',  # Garante ocupação total da largura
        'display': 'block',  # Força comportamento de bloco
        'fontSize': '24px',  # Tamanho adequado
        'color': '#2c3e50'  # Cor contrastante
    }
),
    
    html.Div([
        
        # Linha 1 - Protocolo e Caso
        html.Div([
            html.Div([
                html.Label('Protocolo', style={**item_style, 'minWidth': '120px'}),
                dcc.Dropdown(
                    id='protocolo',
                    placeholder="Selecione o protocolo",
                    options=get_protocolos(),
                    style={'width': '100%'}
                )
            ], style={'flex': 1, 'marginRight': '20px'}),
            
            html.Div([
                html.Label('Caso', style={**item_style, 'minWidth': '120px'}),
                dcc.Input(
                    id='caso',
                    type='number',
                    placeholder='Número do caso',
                    style={'width': '100%'}
                )
            ], style={'flex': 1})
        ], style={'display': 'flex', 'marginBottom': '25px', 'gap': '20px'}),
        
        html.Div([
            html.Div([
                html.Label('Descrição da peça', style=item_style),
                dcc.Input(
                    id='descricao_peca',
                    type='text',
                    placeholder='Descrição da peça',
                    style={'width': '100%'}
                )
            ], style={'flex': 2, 'marginRight': '20px'}),
            
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
            ], style={'flex': 1})
        ], style={'display': 'flex', 'marginBottom': '25px', 'gap': '20px'}),
        
        # Linha 3 - PAE e Prioridade
        html.Div([
            html.Div([
                html.Label('PAE', style=item_style),
                dcc.RadioItems(
                    id='pae',
                    options=[{'label': 'Sim', 'value': 'Sim'}, {'label': 'Não', 'value': 'Não'}],
                    value=None,
                    labelStyle={'display': 'inline-block', 'marginRight': '15px'}
                )
            ], style={'flex': 1, 'marginRight': '30px'}),
            
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
                    labelStyle={'display': 'inline-block', 'marginRight': '15px'}
                )
            ], style={'flex': 1})
        ], style={'display': 'flex', 'marginBottom': '25px', 'gap': '20px'}),
        
       
        html.Div([
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
            ], style={'flex': 1, 'marginRight': '20px'}),
            
            html.Div([
                html.Label('Responsável', style=item_style),
                dcc.Input(
                    id='responsavel',
                    type='text',
                    placeholder='Nome do responsável',
                    style={'width': '100%'}
                )
            ], style={'flex': 1})
        ], style={'display': 'flex', 'marginBottom': '25px', 'gap': '20px'}),
        
        # Observações
html.Div([
    html.Label('Observações', style=item_style),
    dcc.Textarea(
        id='observacoes',
        placeholder='Digite suas observações...',
        style={
            'width': '100%',
            'height': '100px',  # Altura fixa
            'resize': 'vertical',  # Permite redimensionar verticalmente
            'padding': '10px',
            'border': '1px solid #ced4da',
            'borderRadius': '4px',
            'verticalAlign': 'top',  # Alinha o texto no topo
            'lineHeight': 'normal'  # Remove espaçamento extra
        }
    )
], style={'marginBottom': '30px', 'display': 'block'})
        
    ], style={
        'maxWidth': '800px',
        'margin': '0 auto',
        'padding': '30px',
        'backgroundColor': '#f8f9fa',
        'borderRadius': '10px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }),
    
    html.Div([
        html.Button('Salvar', id='salvar-button', n_clicks=0,
                    style={
                        'padding': '10px 30px',
                        'backgroundColor': '#007bff',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '5px',
                        'cursor': 'pointer'
                    }),
        html.Br(),
        html.Div(id='mensagem', style={'padding': '10px', 'textAlign': 'center', 'marginTop': '15px'}),
        dcc.Link("Voltar", href="/cadastro", style={'marginTop': '20px', 'display': 'block'})
    ], style={'textAlign': 'center', 'marginTop': '30px'})
    
], style={
    'padding': '40px 20px',
    'fontFamily': 'Arial, sans-serif'
})

@app.callback(
    Output("mensagem-gerenciamento", "children"),
    Output("tabela-usuarios", "data"),
    Input("cadastrar-usuario-button", "n_clicks"),
    Input("atualizar-usuario-button", "n_clicks"),
    Input("deletar-usuario-button", "n_clicks"),
    State("novo-username", "value"),
    State("novo-password", "value"),
    State("novo-role", "value"),
    State("edit-user-id", "value"),
    State("edit-username", "value"),
    State("edit-password", "value"),
    State("edit-role", "value"),
    State("delete-user-id", "value"),
)
def gerenciar_usuarios(n_clicks_cadastrar, n_clicks_atualizar, n_clicks_deletar,
                       novo_username, novo_password, novo_role,
                       edit_user_id, edit_username, edit_password, edit_role,
                       delete_user_id):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    botao_clicado = ctx.triggered[0]['prop_id'].split('.')[0]

    conn = sqlite3.connect('protocolo.db')
    c = conn.cursor()

    try:
        if botao_clicado == 'cadastrar-usuario-button':
            if not novo_username or not novo_password or not novo_role:
                conn.close()
                return "Preencha todos os campos para cadastrar o usuário.", dash.no_update
            try:
                c.execute("INSERT INTO usuarios (username, password, role) VALUES (?, ?, ?)", 
                          (novo_username, novo_password, novo_role))
                conn.commit()
                mensagem = f"Usuário {novo_username} cadastrado com sucesso!"
            except sqlite3.IntegrityError:
                conn.close()
                return "Usuário já existe!", dash.no_update

        elif botao_clicado == 'atualizar-usuario-button':
            if not edit_user_id:
                conn.close()
                return "Informe o ID do usuário para atualizar.", dash.no_update
            updates = []
            params = []
            if edit_username:
                updates.append("username = ?")
                params.append(edit_username)
            if edit_password:
                updates.append("password = ?")
                params.append(edit_password)
            if edit_role:
                updates.append("role = ?")
                params.append(edit_role)
            if not updates:
                conn.close()
                return "Nenhum campo para atualizar.", dash.no_update
            params.append(edit_user_id)
            query = "UPDATE usuarios SET " + ", ".join(updates) + " WHERE id = ?"
            c.execute(query, tuple(params))
            conn.commit()
            mensagem = "Usuário atualizado com sucesso."

        elif botao_clicado == 'deletar-usuario-button':
            if not delete_user_id:
                conn.close()
                return "Informe o ID do usuário para deletar.", dash.no_update
            c.execute("DELETE FROM usuarios WHERE id = ?", (delete_user_id,))
            conn.commit()
            mensagem = "Usuário deletado com sucesso."

        else:
            conn.close()
            raise dash.exceptions.PreventUpdate

        # Atualiza a tabela após qualquer operação
        c.execute("SELECT id, username, role FROM usuarios")
        users = c.fetchall()
        data = [{'id': u[0], 'username': u[1], 'role': u[2]} for u in users]
        conn.close()

        return mensagem, data

    except Exception as e:
        conn.close()
        return f"Erro: {str(e)}", dash.no_update

# Layout principal
app.layout = html.Div([
    dcc.Store(id="store-protocolos", data=get_protocolos()),
    dcc.Location(id="url", refresh=False),
    dcc.Store(id='last-activity', storage_type='session'),
    dcc.Interval(id='logout-check-interval', interval=60*1000),
    html.Div(id='activity-tracker', n_clicks=0, style={'display': 'none'}),

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

    html.Div([
        dcc.Link("Cadastro de Protocolo", href="/cadastro"),
        dcc.Link("Formulário de Cadastro", href="/formulario"),
        dcc.Link("Visualizar Registros", href="/visualizacao"),
        dcc.Link("Gerenciar Usuários", href="/usuarios")
    ], style={'padding': '10px', 'textAlign': 'center', 'gap': '5rem', 'display': 'flex', 'justifyContent': 'center'}),
    

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
            return dcc.Location(pathname='/cadastro', id='url-redirect')
        return "Credenciais inválidas! Tente novamente."
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
    Output("url", "pathname"),
    Input("logout-button", "n_clicks"),
    prevent_initial_call=True,
    allow_duplicate=True
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
# além de recalcular a cor com base na data prazo.
@app.callback(
    Output("tabela-dados", "data"),
    [Input("atualizar-dados", "n_clicks"),
     Input("buscar-button", "n_clicks")],
    [State("filtro_protocolo", "value"),
     State("buscar-protocolo", "value")],
    prevent_initial_call=True,
    allow_duplicate=True
)
def carregar_dados(n_atualizar, n_buscar, filtro_value, buscar_value):
    ctx = callback_context
    if not ctx.triggered:
        raise Exception("No trigger")
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    conn = sqlite3.connect('protocolo.db')
    c = conn.cursor()
    if current_user.role == 'admin':
        if trigger_id == "buscar-button" and buscar_value:
            c.execute("SELECT * FROM formulario WHERE protocolo LIKE ?", ('%' + buscar_value + '%',))
        elif filtro_value:
            c.execute("SELECT * FROM formulario WHERE protocolo = ?", (filtro_value,))
        else:
            c.execute("SELECT * FROM formulario")
    else:
        user_name = current_user.username
        if trigger_id == "buscar-button" and buscar_value:
            c.execute("SELECT * FROM formulario WHERE responsavel = ? AND responsavel LIKE ?", (user_name, '%' + buscar_value + '%'))
        else:
            c.execute("SELECT * FROM formulario WHERE responsavel = ?", (user_name,))
    rows = c.fetchall()
    conn.close()
    tabela = []
    for row in rows:
        record = list(row)
        pae_value = record[5]
        data_prazo = record[7]
        if record[9] != "green":
            if data_prazo:
                try:
                    if "-" in data_prazo:
                        prazo = datetime.strptime(data_prazo, "%Y-%m-%d").date()
                    else:
                        prazo = datetime.strptime(data_prazo, "%d/%m/%Y").date()
                    dias_restantes = (prazo - datetime.today().date()).days
                    if dias_restantes > 10:
                        record[9] = "amarela"
                    else:
                        record[9] = "vermelha"
                except Exception:
                    record[9] = ""
            else:
                record[9] = ""
        tabela.append({
            "id": record[0],
            "protocolo": record[1],
            "caso": record[2],
            "descricao_peca": record[3],
            "data_distribuicao": record[4],
            "PAE": pae_value,
            "prioridade": record[6],
            "data_prazo": data_prazo,
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
    prevent_initial_call=True,
    allow_duplicate=True
)
def finalizar_protocolo(n_clicks, table_data, selected_rows):
    if n_clicks > 0 and selected_rows is not None and len(selected_rows) > 0:
        selected_index = selected_rows[0]
        record = table_data[selected_index]
        protocolo_id = record["id"]
        conn = sqlite3.connect('protocolo.db')
        c = conn.cursor()
        c.execute("UPDATE formulario SET cor = ? WHERE id = ?", ("green", protocolo_id))
        conn.commit()
        conn.close()
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
