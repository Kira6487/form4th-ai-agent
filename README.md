# FORM4TH AI Agent

Foundation monorepo for the FORM4TH AI Agent platform. Phase 1 provides a
Next.js status dashboard, a modular FastAPI API, PostgreSQL connectivity through
SQLAlchemy/Alembic, and a server-side Gemini provider adapter. Product domains
such as organizations, companies, ingestion, RAG, chat, leads and
integrations are intentionally reserved for later phases.

## Requisitos

- Node.js 20+
- Python 3.12+
- Acceso a un proyecto Supabase/PostgreSQL
- Una API key de Google Gemini para el smoke check de IA
- Docker (opcional, para construir la imagen del backend)

## Variables de entorno

Desde la raíz del repositorio:

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Añade localmente los valores de `GEMINI_API_KEY` y `DATABASE_URL`. El archivo
`.env` nunca debe versionarse. `DATABASE_URL` acepta cualquier PostgreSQL
compatible, incluida una URL del pooler de Supabase; si la contraseña tiene
caracteres especiales debe estar correctamente codificada en la URL.

`NEXT_PUBLIC_API_URL` es la única variable pública del frontend y contiene solo
la URL del backend. Las credenciales de Gemini, Supabase y PostgreSQL son
exclusivamente server-side.

## Instalación y ejecución del frontend

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:3000`. La pantalla comprueba el backend, PostgreSQL y
Gemini al cargar y mediante el botón `Refresh status`; no usa polling agresivo.

## Instalación y ejecución del backend

Linux/macOS:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Endpoints de foundation:

- `GET /health` — disponibilidad de FastAPI.
- `GET /api/v1/health/db` — consulta real `SELECT 1` a PostgreSQL.
- `GET /api/v1/health/ai` — llamada mínima real a Gemini cuando existe la key.

Los dos últimos devuelven HTTP 503 con un mensaje seguro cuando la dependencia
no está configurada o no está disponible.

## Migraciones

La cadena inicial no crea tablas de dominio en Fase 1. Ejecuta desde
`backend/` con `DATABASE_URL` configurada:

```bash
alembic upgrade head
```

La extensión `pgvector` y las tablas de producto se dejan para las fases en las
que sus esquemas estén definidos.

## Testing y validaciones

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

El test unitario de Gemini usa un cliente falso y no consume API. El smoke test
real solo se ejecuta al llamar al endpoint con `GEMINI_API_KEY` configurada.

## Docker

Construye la imagen desde la raíz:

```bash
docker build -f backend/Dockerfile -t form4th-ai-agent-api .
```

El contenedor ejecuta Uvicorn como usuario no root en el puerto `8000`. Pasa las
variables de entorno al ejecutar el contenedor mediante tu gestor local o de
secretos; nunca las copies dentro de la imagen.

## Ramas y alcance

Cada fase se desarrolla en una rama propia. Esta implementación corresponde a:

```text
feature/fase-1-foundation
```

Las siguientes ramas previstas están documentadas en `Docs/AGENTS.md`; no se
crean por adelantado. El flujo recomendado para publicar esta fase es:

```bash
git status
git branch --show-current
git log --oneline -10
git push -u origin feature/fase-1-foundation
```

Después, abre un Pull Request desde `feature/fase-1-foundation` hacia `main`,
revisa los checks automatizados y realiza el merge mediante el flujo protegido
del repositorio. Este agente no hace push ni crea Pull Requests.
