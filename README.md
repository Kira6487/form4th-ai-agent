# FORM4TH AI Agent

Monorepo for the FORM4TH AI Agent platform. Phases 1 and 2 provide a Next.js
foundation, Supabase Auth integration, a modular FastAPI API, PostgreSQL
connectivity through SQLAlchemy/Alembic, tenant authorization, and basic
company management, and Phase 3 knowledge ingestion. Embeddings, RAG, chat,
leads and integrations remain reserved for later phases.

## Requisitos

- Node.js 20+
- Python 3.12+
- Acceso a un proyecto Supabase/PostgreSQL
- Una API key de Google Gemini para el smoke check de IA
- Un proyecto Supabase con Auth habilitado
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

Para Fase 2 configura también `NEXT_PUBLIC_SUPABASE_URL` y
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. Son valores públicos para el navegador;
nunca uses una service role key en el frontend.

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

## Authentication y multi-tenancy

El registro y login utilizan Supabase Auth. El frontend restaura la sesión,
envía `Authorization: Bearer ...` al backend y protege `/dashboard` y
`/onboarding` mediante `proxy.ts`. FastAPI verifica JWT usando el JWKS público
de Supabase con cache TTL y deriva la identidad desde el token; nunca confía en
`user_id`, `organization_id` o roles enviados por el navegador.

El onboarding crea la organización y su membership `owner` en una transacción.
Los roles iniciales son `owner`, `admin` y `member`: todos pueden leer sus
recursos y solo owner/admin puede crear, editar o archivar companies.

Rutas de Fase 2: `/login`, `/register`, `/forgot-password`, `/onboarding`,
`/dashboard`, `/dashboard/companies`, `/dashboard/companies/new` y
`/dashboard/companies/[id]`.

Endpoints nuevos: `GET /api/v1/me`, `POST/GET /api/v1/organizations`,
`GET /api/v1/organizations/{id}` y CRUD de companies bajo
`/api/v1/organizations/{organization_id}/companies`.

## Knowledge ingestion

Fase 3 convierte Website, Manual text y PDF en contenido normalizado. Website
usa Firecrawl asincrono y limitado por `FIRECRAWL_MAX_PAGES`; PDF valida MIME,
firma `%PDF-` y tamano antes de extraer texto con `pypdf`. Los PDFs usan el
bucket privado de Supabase Storage indicado por `SUPABASE_STORAGE_BUCKET`; OCR
no esta soportado en Fase 3.

El pipeline es `Source -> Ingestion Run -> Document -> Chunk`. El normalizador
conserva encabezados, listas y parrafos; el chunker usa una estimacion neutral
de tokens configurable con `CHUNK_TARGET_APPROX_TOKENS` (800) y
`CHUNK_OVERLAP_APPROX_TOKENS` (100). Cada documento y chunk tiene hash SHA-256.
Una reindexacion solo activa la nueva version despues de completarse; si falla,
la version anterior permanece activa.

Knowledge esta disponible en `/dashboard/knowledge` y
`/dashboard/companies/[id]/knowledge`, con altas, estado/polling, reindex,
disable y previews paginados de documentos/chunks. No se crean embeddings,
vectores ni busqueda en esta fase.

## Migrations y RLS

Migration `0003_knowledge_ingestion` agrega las tablas tenant-aware de Knowledge
(`knowledge_sources`, `knowledge_ingestion_runs`, `knowledge_documents` y
`knowledge_chunks`) con indices y policies RLS. No se declara validacion RLS
real sin un proyecto Supabase de desarrollo.

Migration `0002_multitenancy` crea `profiles`, `organizations`,
`organization_members` y `companies`, con constraints, índices, RLS y policies.
Ejecuta desde `backend/` con `DATABASE_URL` configurada:

```bash
alembic upgrade head
```

La estrategia reproducible para verificar RLS con Supabase está en
`supabase/tests/README.md`. No se declara ejecutada sin un proyecto Supabase
real. pgvector y embeddings pertenecen a fases posteriores.

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
feature/fase-3-knowledge-ingestion
```

Las siguientes ramas previstas están documentadas en `Docs/AGENTS.md`; no se
crean por adelantado. El flujo recomendado para publicar esta fase es:

```bash
git status
git branch --show-current
git log --oneline -10
git push -u origin feature/fase-3-knowledge-ingestion
```

Después, abre un Pull Request desde `feature/fase-3-knowledge-ingestion` hacia `main`,
revisa los checks automatizados y realiza el merge mediante el flujo protegido
del repositorio. Este agente no hace push ni crea Pull Requests.
