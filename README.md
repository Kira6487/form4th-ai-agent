# FORM4TH AI Agent

Monorepo for the FORM4TH AI Agent platform. Phases 1 and 2 provide a Next.js
foundation, Supabase Auth integration, a modular FastAPI API, PostgreSQL
connectivity through SQLAlchemy/Alembic, tenant authorization, and basic
company management. Phase 3 adds knowledge ingestion and Phase 4 adds Gemini
embeddings, pgvector retrieval and a non-generative RAG context preview. Phase 5
adds configurable private agents, persisted dashboard conversations, grounded
Gemini responses and a test chat. Leads, tools and public integrations remain
reserved for later phases.

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

Los tests unitarios de Gemini y embeddings usan clientes falsos y no consumen
API. Los smoke tests reales solo se ejecutan con `GEMINI_API_KEY` y
`DATABASE_URL` configuradas.

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
disable y previews paginados de documentos/chunks. Los chunks nuevos quedan
`pending` hasta que un owner/admin ejecuta indexación por lotes. Fase 4 usa
`gemini-embedding-2` con 768 dimensiones, la cadena documental
`title: ... | text: ...` y la cadena de consulta
`task: search result | query: ...`; se configura `EMBEDDING_BATCH_SIZE` (50).
La migración `0004_embeddings_rag` habilita pgvector, agrega metadatos de
modelo/estado y crea un índice HNSW cosine. El retrieval filtra primero por
`organization_id`, `company_id`, fuente/documento/chunk activos y estado
`ready`, y aplica `RAG_MIN_SIMILARITY` antes de devolver resultados.

Endpoints de Fase 4:

- `POST .../knowledge/embeddings/index` — indexa un lote de chunks pendientes.
- `POST .../knowledge/sources/{source_id}/embeddings/reindex` — re-usa o
  re-embebe una fuente (`force` permite regenerar todo).
- `POST .../knowledge/search` — devuelve top-K chunks con similitud y citas.
- `POST .../knowledge/rag-preview` — construye contexto/citas sin llamar a un
  modelo generativo.

Los endpoints de search y RAG preview nunca devuelven embeddings al navegador.

## AI Agent y Chat (Fase 5)

Cada empresa puede configurar varios agentes con nombre, rol, objetivo, tono,
idioma, instrucciones, modelo, estado y límites de generación. La pantalla
`/dashboard/companies/[id]/agent` permite guardar la configuración y probar un
agente privado desde el dashboard; todavía no existe un canal público.

El flujo de chat es `pregunta -> embedding/retrieval -> contexto RAG ->
instrucciones del agente -> Gemini Interactions API -> respuesta visible ->
persistencia`. La aplicación usa `google-genai`, `store=false` y mantiene el
historial reciente en PostgreSQL/Supabase, con `CHAT_HISTORY_MAX_MESSAGES=12`.
No depende de `previous_interaction_id` como fuente de verdad. La integración
encapsulada no persiste ni devuelve reasoning, thoughts, trazas ni respuestas
raw del proveedor.

Las instrucciones confiables y el bloque `RETRIEVED KNOWLEDGE` se envían como
secciones estructuralmente separadas. El contenido recuperado se considera
datos no confiables y nunca instrucciones. Si no hay contexto relevante, el
backend devuelve un fallback seguro y no llama al modelo generativo. Las
respuestas persistidas guardan solo texto visible, IDs de chunks, fuentes y
usage/latencia segura cuando Gemini la entrega.

Endpoints principales:

- `POST/GET/PATCH .../companies/{company_id}/agents` — configuración tenant-aware.
- `POST .../agents/{agent_id}/conversations` — crea sesiones dashboard.
- `GET .../conversations/{conversation_id}/messages` — historial visible.
- `POST .../conversations/{conversation_id}/messages` — respuesta no streaming.
- `POST .../conversations/{conversation_id}/messages/stream` — SSE con persistencia al completar.

Fase 5 no implementa leads, lead qualification, tool calling, CRM, Calendar,
WhatsApp ni widget. El widget embebible pertenece a Fase 8.

## Migrations y RLS

Migration `0003_knowledge_ingestion` agrega las tablas tenant-aware de Knowledge
(`knowledge_sources`, `knowledge_ingestion_runs`, `knowledge_documents` y
`knowledge_chunks`) con indices y policies RLS. No se declara validacion RLS
real sin un proyecto Supabase de desarrollo. Migration `0004_embeddings_rag`
habilita la extensión `vector`, agrega `vector(768)` y el índice HNSW; no llama
a Gemini durante la migración. SQLite se usa solo para tests que no ejecutan
operadores vectoriales.

Migration `0005_ai_agents_chat` agrega agentes, conversaciones y mensajes con
RLS tenant-aware. Los usuarios autenticados solo pueden insertar mensajes de
rol `user`; las respuestas del agente se persisten desde el backend con el
rol de servicio.

Migration `0002_multitenancy` crea `profiles`, `organizations`,
`organization_members` y `companies`, con constraints, índices, RLS y policies.
Ejecuta desde `backend/` con `DATABASE_URL` configurada:

```bash
alembic upgrade head
```

La estrategia reproducible para verificar RLS con Supabase está en
`supabase/tests/README.md`. No se declara ejecutada sin un proyecto Supabase
real.

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
feature/fase-5-ai-agent-chat
```

Las siguientes ramas previstas están documentadas en `Docs/AGENTS.md`; no se
crean por adelantado. El flujo recomendado para publicar esta fase es:

```bash
git status
git branch --show-current
git log --oneline -10
git push -u origin feature/fase-5-ai-agent-chat
```

Después, abre un Pull Request desde `feature/fase-5-ai-agent-chat` hacia `main`,
revisa los checks automatizados y realiza el merge mediante el flujo protegido
del repositorio. Este agente no hace push ni crea Pull Requests.
