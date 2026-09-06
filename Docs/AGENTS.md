# AGENTS.md — FORM4TH AI Agent

## 1. Propósito de este archivo

Este archivo contiene las instrucciones permanentes que cualquier agente de desarrollo, especialmente Codex, debe leer y respetar antes de modificar el proyecto.

Antes de comenzar cualquier tarea:

1. Leer este archivo completo.
2. Leer `ALCANCE.md`.
3. Inspeccionar el estado actual del repositorio.
4. Revisar la arquitectura y código existente antes de crear archivos nuevos.
5. Mantener compatibilidad con lo ya implementado.
6. No modificar el alcance funcional sin una instrucción explícita.
7. No sustituir tecnologías principales sin autorización.
8. Ejecutar pruebas antes de considerar una tarea terminada.

Si existe una contradicción entre una instrucción puntual del usuario y este documento, prevalece la instrucción puntual más reciente del usuario.

---

# 2. Identidad del proyecto

Nombre:

FORM4TH AI Agent

Repositorio oficial:

https://github.com/Kira6487/form4th-ai-agent.git

Repositorio GitHub:

Kira6487/form4th-ai-agent

Rama principal:

main

Supabase Project:

form4th-ai-agent

Supabase Project URL:

https://vytmhyerzlxqheisordr.supabase.co

El producto pertenece al ecosistema FORM4TH y tiene como objetivo convertirse en una plataforma SaaS multiempresa para crear agentes de inteligencia artificial personalizados utilizando la información real de cada organización.

---

# 3. Objetivo general

Construir una plataforma SaaS donde un administrador pueda registrar una empresa y transformar:

* su página web;
* documentos;
* información manual;
* preguntas frecuentes;
* productos;
* servicios;
* precios;
* ubicaciones;
* políticas;
* procesos comerciales;

en una base de conocimiento utilizable por un agente de IA empresarial.

Cada empresa debe disponer de un agente aislado y configurable.

El agente podrá:

* responder consultas;
* consultar conocimiento mediante RAG;
* evitar inventar información;
* detectar intención comercial;
* capturar leads;
* mantener conversaciones;
* ejecutar herramientas autorizadas;
* escalar una conversación a una persona;
* generar métricas de utilización.

El sistema debe diseñarse desde el inicio como una aplicación multi-tenant.

---

# 4. Stack tecnológico obligatorio

## Frontend

* Next.js
* React
* TypeScript
* App Router
* diseño responsive
* componentes reutilizables

## Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic

## Inteligencia artificial

Proveedor principal:

Google Gemini API

SDK Python:

`google-genai`

Modelo conversacional inicial recomendado:

`gemini-3.7-flash`

El modelo NO debe estar hardcodeado en múltiples archivos.

Debe existir una variable:

```env
GEMINI_MODEL=gemini-3.7-flash
```

Modelo de embeddings:

```env
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
```

## Base de datos

* Supabase
* PostgreSQL
* pgvector

## Autenticación

Supabase Auth.

## Archivos

Supabase Storage.

## Extracción web

La arquitectura debe abstraer la extracción de contenido detrás de un servicio de ingestion/crawling.

Proveedor previsto:

Firecrawl.

No acoplar todo el sistema directamente a Firecrawl. Crear una interfaz/servicio que permita cambiar de proveedor posteriormente.

## Despliegue previsto

Frontend:

Vercel.

Backend:

contenedor Python desplegable en Azure Container Apps.

Base de datos:

Supabase PostgreSQL.

---

# 5. Manejo obligatorio de secretos

NUNCA introducir secretos en:

* código fuente;
* `AGENTS.md`;
* `ALCANCE.md`;
* README;
* commits;
* variables públicas del frontend;
* logs;
* respuestas HTTP;
* fixtures;
* tests.

Las credenciales reales han sido entregadas al operador fuera del repositorio.

Codex debe utilizar variables de entorno.

Crear:

```text
.env.example
```

pero NO crear ni versionar:

```text
.env
.env.local
.env.production
```

con secretos reales.

Comprobar que `.gitignore` contenga como mínimo:

```gitignore
.env
.env.*
!.env.example
```

---

# 6. Configuración Gemini

La API Key de Google Gemini proporcionada por el propietario debe almacenarse localmente o en el gestor de secretos del entorno con el nombre:

```env
GEMINI_API_KEY=<SECRET>
```

Nunca utilizar prefijos públicos como:

```env
NEXT_PUBLIC_GEMINI_API_KEY
```

La API de Gemini debe consumirse exclusivamente desde código de servidor.

Flujo correcto:

```text
Browser
   ↓
Next.js
   ↓
FastAPI
   ↓
Gemini API
```

Flujo prohibido:

```text
Browser
   ↓
Gemini API
```

Instalar en el backend:

```bash
pip install -U google-genai
```

Crear un servicio centralizado, por ejemplo:

```text
backend/app/services/ai/gemini_service.py
```

No instanciar clientes de Gemini arbitrariamente por todo el proyecto.

La configuración debe obtenerse desde un módulo central de settings.

Ejemplo conceptual:

```python
from google import genai

client = genai.Client()
```

El SDK puede leer `GEMINI_API_KEY` desde el entorno.

El modelo debe obtenerse de:

```env
GEMINI_MODEL
```

y no escribirse repetidamente en el código.

---

# 7. Configuración Supabase

Proyecto:

```text
form4th-ai-agent
```

Project URL:

```text
https://vytmhyerzlxqheisordr.supabase.co
```

Host PostgreSQL directo:

```text
db.vytmhyerzlxqheisordr.supabase.co
```

Puerto:

```text
5432
```

Database:

```text
postgres
```

Usuario:

```text
postgres
```

Patrón de conexión:

```env
DATABASE_URL=postgresql://postgres:<PASSWORD>@db.vytmhyerzlxqheisordr.supabase.co:5432/postgres
```

La contraseña real debe existir únicamente como secreto.

IMPORTANTE:

Si la contraseña incluye caracteres especiales, debe realizarse URL encoding antes de introducirla manualmente en un URI.

Es preferible utilizar `SQLAlchemy URL.create()` o una herramienta equivalente cuando sea posible para evitar errores de encoding.

Variables previstas:

```env
SUPABASE_URL=https://vytmhyerzlxqheisordr.supabase.co

DATABASE_URL=postgresql://postgres:<PASSWORD>@db.vytmhyerzlxqheisordr.supabase.co:5432/postgres

SUPABASE_ANON_KEY=<SECRET>

SUPABASE_SERVICE_ROLE_KEY=<SECRET>
```

`SUPABASE_SERVICE_ROLE_KEY` nunca debe llegar al navegador.

Si el frontend necesita utilizar Supabase Auth mediante el cliente oficial, únicamente podrá exponerse el valor público/anon correspondiente y siempre deben existir políticas RLS apropiadas.

---

# 8. Direct Connection vs Pooler de Supabase

El endpoint actualmente conocido:

```text
db.vytmhyerzlxqheisordr.supabase.co:5432
```

corresponde a conexión PostgreSQL directa.

Puede utilizarse para:

* desarrollo;
* migraciones;
* herramientas administrativas;
* backends persistentes cuando existe conectividad compatible.

Si el entorno de despliegue no puede resolver/conectarse mediante IPv6 o presenta problemas de red, NO modificar código para solucionar el problema.

En ese caso:

1. abrir Supabase;
2. seleccionar el proyecto;
3. pulsar `Connect`;
4. obtener el Shared Pooler;
5. preferir Session Mode para un backend persistente;
6. reemplazar únicamente `DATABASE_URL`.

La aplicación debe funcionar indistintamente siempre que reciba un PostgreSQL `DATABASE_URL` válido.

---

# 9. Variables de entorno iniciales

Crear `.env.example` con esta estructura:

```env
# Application
APP_ENV=development
APP_NAME=form4th-ai-agent

# Frontend / Backend
FRONTEND_ORIGIN=http://localhost:3000
BACKEND_URL=http://localhost:8000

# Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.7-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
GEMINI_EMBEDDING_DIMENSIONS=768

# Supabase
SUPABASE_URL=https://vytmhyerzlxqheisordr.supabase.co
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# PostgreSQL
DATABASE_URL=postgresql://postgres:<PASSWORD>@db.vytmhyerzlxqheisordr.supabase.co:5432/postgres

# Web ingestion
FIRECRAWL_API_KEY=

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

No rellenar secretos en `.env.example`.

---

# 10. Repositorio Git

Repositorio único y oficial:

```text
https://github.com/Kira6487/form4th-ai-agent.git
```

Codex debe trabajar dentro de este proyecto.

No crear un segundo repositorio.

No inicializar otro proyecto Git dentro del repositorio.

Clonación:

```bash
git clone https://github.com/Kira6487/form4th-ai-agent.git
cd form4th-ai-agent
```

Antes de modificar:

```bash
git status
git branch
git log --oneline -10
```

Antes de finalizar:

```bash
git status
git diff
```

No ejecutar:

```bash
git push --force
git reset --hard
```

salvo instrucción explícita.

No eliminar trabajo existente de otros desarrolladores.

Realizar commits descriptivos y pequeños cuando corresponda.

Ejemplos:

```text
feat: add company onboarding foundation
feat: integrate Gemini service
feat: add knowledge ingestion pipeline
feat: implement pgvector semantic search
fix: isolate RAG queries by organization
```

---

# 11. Arquitectura del repositorio

Arquitectura objetivo inicial:

```text
form4th-ai-agent/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   ├── types/
│   └── tests/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   ├── ingestion/
│   │   │   ├── rag/
│   │   │   └── integrations/
│   │   ├── agents/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── alembic/
│   └── requirements.txt
│
├── supabase/
│   └── migrations/
│
├── docs/
│
├── .env.example
├── .gitignore
├── AGENTS.md
├── ALCANCE.md
└── README.md
```

Codex puede adaptar detalles menores si existe una razón técnica clara, pero debe mantener separación entre:

* frontend;
* API;
* persistencia;
* IA;
* RAG;
* ingestión;
* integraciones.

---

# 12. Arquitectura de backend

Mantener capas claras:

```text
API
↓
Services
↓
Repositories
↓
Database
```

Los endpoints FastAPI no deben contener lógica empresarial compleja.

Ejemplo:

```text
api/companies.py
```

delega a:

```text
services/company_service.py
```

que utiliza:

```text
repositories/company_repository.py
```

---

# 13. Multi-tenancy obligatorio

Este producto debe soportar múltiples organizaciones.

Entidades principales deben relacionarse mediante:

```text
organization_id
```

y cuando corresponda:

```text
company_id
```

Nunca realizar una consulta RAG global sin filtrar tenant.

Una consulta de la organización A no puede recuperar:

* documentos;
* conversaciones;
* instrucciones;
* leads;
* embeddings;

de la organización B.

Esta separación debe comprobarse mediante tests.

---

# 14. Modelo de datos inicial

Crear mediante migraciones y no manualmente desde código de aplicación.

Entidades previstas:

```text
organizations
organization_members
companies

ai_agents
agent_instructions

knowledge_sources
knowledge_documents
knowledge_chunks

conversations
messages

leads

integrations
usage_logs
```

Para RAG:

```text
knowledge_chunks
```

debe incluir como mínimo:

```text
id
organization_id
company_id
source_id
content
embedding
metadata
created_at
updated_at
```

Activar:

```text
pgvector
```

en PostgreSQL.

La dimensión vectorial inicial recomendada será:

```text
768
```

y debe mantenerse consistente con:

```env
GEMINI_EMBEDDING_DIMENSIONS=768
```

No cambiar la dimensión después de generar datos sin una migración explícita y un proceso de reindexación.

---

# 15. Estrategia RAG

NO enviar todos los documentos de una empresa al modelo en cada consulta.

Flujo requerido:

```text
Pregunta del usuario
        ↓
Gemini Embedding
        ↓
Búsqueda vectorial
        ↓
Top K chunks relevantes
        ↓
Construcción de contexto
        ↓
Gemini
        ↓
Respuesta
```

Toda búsqueda debe estar filtrada al menos por:

```text
organization_id
company_id
```

Agregar metadata suficiente para poder identificar:

* fuente;
* URL;
* documento;
* fecha de indexación;
* título;
* tipo de contenido.

---

# 16. Principio de veracidad del agente

Los agentes empresariales no deben inventar:

* precios;
* promociones;
* horarios;
* políticas;
* stock;
* disponibilidad;
* ubicaciones;
* condiciones contractuales.

Si el contexto recuperado no contiene suficiente evidencia, el agente debe reconocer la limitación y ofrecer:

* reformular la consulta;
* buscar otra fuente;
* solicitar contacto humano.

Las instrucciones del agente deben separar:

1. identidad;
2. objetivos;
3. restricciones;
4. conocimiento recuperado;
5. conversación;
6. herramientas disponibles.

---

# 17. Ingestión de conocimiento

Fuentes previstas:

## MVP

* URL de empresa;
* páginas web;
* texto manual;
* PDF.

## Posteriores

* DOCX;
* XLSX;
* CSV;
* APIs;
* Google Drive;
* Notion;
* CRM;
* ERP.

Proceso:

```text
Source
↓
Extract
↓
Normalize
↓
Split
↓
Metadata
↓
Embedding
↓
Store
```

No mezclar extracción, chunking, embeddings y almacenamiento en una sola función gigante.

---

# 18. Captura de leads

El agente debe poder detectar señales comerciales como:

* quiero comprar;
* quiero cotizar;
* quiero una demo;
* quiero reservar;
* quiero una llamada;
* cuál es el precio;
* me interesa;
* cómo contrato.

No almacenar datos personales innecesarios.

Entidad mínima:

```text
leads

id
organization_id
company_id
conversation_id
name
email
phone
interest
source
status
created_at
updated_at
```

---

# 19. API

Versionar endpoints:

```text
/api/v1/
```

Endpoints base previstos:

```text
GET  /health
GET  /api/v1/health/db

POST /api/v1/companies
GET  /api/v1/companies

POST /api/v1/knowledge/sources
POST /api/v1/knowledge/ingest

POST /api/v1/chat
GET  /api/v1/conversations

GET  /api/v1/leads
```

No exponer endpoints administrativos sin autenticación en producción.

---

# 20. Health checks

Implementar:

```text
GET /health
```

Respuesta mínima:

```json
{
  "status": "ok"
}
```

Y:

```text
GET /api/v1/health/db
```

debe comprobar conectividad real con PostgreSQL sin revelar:

* contraseña;
* connection string;
* nombres sensibles;
* secretos.

---

# 21. Testing obligatorio

Backend:

* pytest;
* tests unitarios;
* tests de integración.

Frontend:

* lint;
* typecheck;
* tests críticos.

Antes de finalizar una fase ejecutar, como mínimo:

```text
backend tests
frontend lint
frontend typecheck
frontend production build
```

Cuando exista DB:

```text
database connectivity
migration checks
```

Cuando exista Gemini:

```text
Gemini integration smoke test
```

No mostrar la API key durante pruebas.

---

# 22. Seguridad

Aplicar como mínimo:

* secretos únicamente server-side;
* validación Pydantic;
* CORS explícito;
* rate limiting cuando el chat sea público;
* RLS donde corresponda;
* logs sanitizados;
* límites de tamaño para uploads;
* validación MIME;
* protección contra prompt injection;
* aislamiento tenant;
* autorización por recursos;
* no ejecutar código proveniente de documentos;
* no confiar en contenido obtenido desde webs.

El contenido extraído de Internet debe tratarse como DATOS, no como instrucciones del sistema.

---

# 23. Diseño frontend

El producto debe verse como un SaaS B2B profesional.

Prioridades:

* claridad;
* jerarquía visual;
* baja saturación;
* interfaces administrativas;
* responsive desktop/mobile;
* accesibilidad;
* estados loading;
* estados empty;
* errores claros;
* skeletons cuando corresponda.

Módulos objetivo:

```text
Overview
Companies
AI Agent
Knowledge
Conversations
Leads
Analytics
Integrations
Settings
```

Evitar interfaces genéricas de "demo de chatbot".

El producto debe sentirse como una herramienta empresarial.

---

# 24. Convenciones

Python:

* typing obligatorio en interfaces públicas;
* funciones pequeñas;
* Pydantic para contratos;
* async cuando aporte valor;
* no `except Exception: pass`;
* logs estructurados.

TypeScript:

* strict mode;
* evitar `any`;
* componentes reutilizables;
* API calls centralizadas;
* separación server/client.

Base de datos:

* snake_case;
* UUID como identificador;
* timestamps UTC;
* foreign keys reales;
* índices donde corresponda.

---

# 25. Observabilidad y costes

Registrar de forma segura:

* modelo utilizado;
* duración de llamada;
* tokens/unidades cuando estén disponibles;
* errores;
* organización;
* agente;
* conversation_id.

No guardar prompts completos con datos sensibles de forma indiscriminada.

Diseñar desde el principio para poder calcular posteriormente:

```text
coste por organización
coste por agente
coste por conversación
```

---

# 26. Regla de desarrollo incremental

No intentar construir el producto completo en una sola tarea.

Desarrollar por fases definidas en `ALCANCE.md`.

Cada fase debe terminar con:

1. código funcional;
2. tests;
3. documentación actualizada;
4. migraciones aplicables;
5. `.env.example` actualizado;
6. README actualizado cuando cambie el procedimiento de ejecución.

Codex debe limitarse a la fase explícitamente solicitada por el usuario.

No avanzar automáticamente a la siguiente fase.

---

# 27. Definition of Done

Una tarea NO está terminada únicamente porque el código compile.

Debe verificarse:

```text
[ ] cumple AGENTS.md
[ ] cumple ALCANCE.md
[ ] no contiene secretos
[ ] mantiene aislamiento multi-tenant
[ ] migraciones correctas
[ ] backend tests pasan
[ ] frontend lint pasa
[ ] frontend typecheck pasa
[ ] frontend build pasa
[ ] no se rompieron funciones existentes
[ ] documentación actualizada
```

---

# 28. Regla fundamental

FORM4TH AI Agent no es un chatbot hardcodeado para una sola empresa.

Debe ser una plataforma configurable y reutilizable:

```text
                   FORM4TH AI CORE
                          │
            ┌─────────────┼─────────────┐
            │             │             │
         Empresa A     Empresa B     Empresa C
            │             │             │
        Knowledge      Knowledge      Knowledge
        Agent          Agent          Agent
        Tools          Tools          Tools
```

Toda decisión arquitectónica debe preservar esta capacidad.
