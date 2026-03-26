# US-01 — Autenticação e Gestão de Usuários

## Objetivo

Permitir login seguro na plataforma e gerenciar contas de usuários com controle de papéis.
Toda a plataforma é fechada — sem auto-cadastro; contas criadas apenas por `admin`.

## Papéis (roles)

| Role    | Permissões                                                                          |
|---------|-------------------------------------------------------------------------------------|
| `admin` | Tudo: cria/remove usuários, acessa revisão (`/review/*`), coleta, anota, dashboard  |
| `user`  | Coleta, limpeza, anotação e dashboard                                               |

Papéis verificados via dependência FastAPI em cada rota. Um usuário tem exatamente um papel.

---

## Contrato de API

### `POST /auth/login`

**Request:**
```json
{ "username": "string", "password": "string" }
```

**Response 200:**
```json
{ "access_token": "string", "token_type": "bearer" }
```

**Erros:**
- `401` — credenciais inválidas (mensagem genérica — nunca indicar qual campo está errado)

---

### `POST /auth/logout`

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "detail": "Logout realizado com sucesso." }
```

---

### `GET /users/`
Lista todos os usuários. Requer `admin`.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "username": "string",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### `POST /users/`
Cria novo usuário. Requer `admin`.

**Request:**
```json
{ "username": "string", "password": "string", "role": "user" }
```

**Response 201:**
```json
{ "id": "uuid", "username": "string", "role": "user", "created_at": "2024-01-01T00:00:00Z" }
```

**Erros:**
- `409` — username já existe
- `422` — role inválida ou password < 8 caracteres

---

### `DELETE /users/{user_id}`
Remove usuário. Requer `admin`.

**Erros:**
- `404` — usuário não encontrado
- `403` — tentativa de remover a si mesmo

---

## Schema de banco (SQLAlchemy)

```python
# models/user.py
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user')", name="ck_valid_role"),
    )
```

---

## Schemas Pydantic

```python
# schemas/user.py
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)
    role: Literal["admin", "user"] = "user"

class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## Service — pontos críticos

```python
# services/auth.py
def authenticate_user(db, username, password) -> User | None:
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user or not verify_password(password, user.hashed_password):
        return None  # nunca revelar qual campo falhou
    return user

# Dependência reutilizável
def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return current_user
```

---

## Frontend — componentes sugeridos

```
pages/Auth/
├── LoginPage.tsx         # formulário de login, armazena token no AuthContext
└── useAuth.ts            # hook: login(), logout(), currentUser, isAdmin

pages/Users/              # visível apenas para admin
├── UsersPage.tsx         # lista + criar + remover
├── CreateUserModal.tsx   # formulário com seleção de papel
└── useUsers.ts

components/
└── ProtectedRoute.tsx    # redireciona se não autenticado ou sem permissão de role
```

**Token:** `localStorage`, limpo no logout.
**AuthContext:** provê `token`, `user` (com `role`) e funções `login`/`logout` para toda a árvore.

---

## Testes obrigatórios (Pytest)

- Login com credenciais válidas retorna JWT
- Login com credenciais inválidas retorna 401 genérico (sem indicar qual campo)
- Rota protegida sem token retorna 401
- `user` tentando acessar `GET /users/` retorna 403
- `admin` criando usuário retorna 201
- Senha não armazenada em texto plano (`hashed_password != plain_password`)
- Token expirado retorna 401

---

## Dependências com outras USs

- **Todas as outras USs** dependem desta — JWT gerado aqui é enviado em toda requisição
- `require_admin` reutilizado em US-05 (`/review/*`) e nos endpoints `/users/*`
