# ALCANCE.md — FORM4TH AI Agent

## 1. Nombre del producto

FORM4TH AI Agent

---

# 2. Visión

FORM4TH AI Agent será una plataforma SaaS B2B que permita convertir el conocimiento digital y operativo de una empresa en un agente de inteligencia artificial configurable.

El producto no pretende entrenar modelos fundacionales propios.

La inteligencia generativa será proporcionada inicialmente por Google Gemini.

La diferenciación del producto estará en:

* organización del conocimiento;
* RAG;
* personalización empresarial;
* herramientas;
* automatizaciones;
* integración con sistemas;
* generación de leads;
* trazabilidad;
* analítica;
* experiencia de administración.

---

# 3. Problema

Muchas empresas poseen información distribuida entre:

* sitios web;
* PDFs;
* documentos internos;
* preguntas frecuentes;
* catálogos;
* hojas de cálculo;
* correos;
* CRM;
* ERP;
* conocimiento de trabajadores.

Los chatbots tradicionales requieren configuración manual y frecuentemente ofrecen respuestas rígidas o poco contextualizadas.

FORM4TH AI Agent debe permitir que una empresa centralice dicho conocimiento y lo utilice mediante un agente de IA que pueda responder utilizando información verificable y posteriormente ejecutar acciones empresariales.

---

# 4. Objetivo principal

Permitir crear un agente empresarial funcional mediante un flujo similar a:

```text
Registrar empresa
       ↓
Ingresar website
       ↓
Extraer información
       ↓
Generar perfil empresarial
       ↓
Agregar documentos
       ↓
Procesar conocimiento
       ↓
Crear embeddings
       ↓
Guardar en pgvector
       ↓
Configurar agente
       ↓
Probar agente
       ↓
Publicar
```

La meta futura es lograr que el onboarding básico de una empresa pueda completarse en aproximadamente 10–15 minutos una vez que la plataforma se encuentre madura.

---

# 5. Arquitectura tecnológica

```text
                    ┌─────────────────────┐
                    │      NEXT.JS        │
                    │  Dashboard + Chat   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      FASTAPI        │
                    │       Python        │
                    └──────┬─────┬────────┘
                           │     │
                 ┌─────────┘     └──────────────┐
                 ▼                              ▼
        ┌─────────────────┐            ┌─────────────────┐
        │  GEMINI API     │            │ WEB INGESTION   │
        │                 │            │   Firecrawl     │
        └────────┬────────┘            └────────┬────────┘
                 │                              │
                 └──────────────┬───────────────┘
                                ▼
                       ┌───────────────────┐
                       │     SUPABASE      │
                       │                   │
                       │ PostgreSQL        │
                       │ pgvector          │
                       │ Auth              │
                       │ Storage           │
                       └───────────────────┘
```

---

# 6. Infraestructura existente

## GitHub

Repositorio:

```text
https://github.com/Kira6487/form4th-ai-agent.git
```

Proyecto:

```text
Kira6487/form4th-ai-agent
```

Rama principal:

```text
main
```

Todo el código del producto debe mantenerse en este repositorio.

---

# 7. Supabase

Nombre del proyecto:

```text
form4th-ai-agent
```

Project URL:

```text
https://vytmhyerzlxqheisordr.supabase.co
```

PostgreSQL host:

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

URI conceptual:

```text
postgresql://postgres:<PASSWORD>@db.vytmhyerzlxqheisordr.supabase.co:5432/postgres
```

Las credenciales reales deben introducirse mediante variables de entorno y nunca incorporarse al repositorio.

Variable principal:

```env
DATABASE_URL=
```

Si la conexión directa presenta incompatibilidad de red en producción, deberá utilizarse el Shared Pooler proporcionado por Supabase sin modificar la lógica del aplicativo.

---

# 8. Gemini

Proveedor inicial de IA:

Google Gemini API.

La credencial proporcionada por el propietario se utilizará mediante:

```env
GEMINI_API_KEY=
```

Modelo conversacional inicial:

```env
GEMINI_MODEL=gemini-3.7-flash
```

Modelo de embeddings:

```env
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
```

Dimensiones iniciales para RAG:

```env
GEMINI_EMBEDDING_DIMENSIONS=768
```

El proveedor debe estar encapsulado detrás de una capa de servicio.

El dominio de la aplicación no debe depender directamente de clases específicas del SDK de Gemini.

Objetivo futuro:

poder agregar otros proveedores sin reescribir:

* conversaciones;
* RAG;
* tenants;
* base de conocimiento;
* leads;
* analítica.

---

# 9. Usuarios objetivo

## Administrador FORM4TH

Puede:

* administrar organizaciones;
* revisar consumo;
* administrar clientes;
* diagnosticar agentes;
* configurar funciones globales.

## Administrador de empresa

Puede:

* configurar su empresa;
* configurar agentes;
* añadir conocimiento;
* revisar conversaciones;
* revisar leads;
* consultar analítica;
* configurar integraciones.

## Miembro de empresa

Puede obtener permisos limitados según rol.

## Usuario final

Interactúa con el agente desde:

* widget web;
* página pública;
* canales futuros.

---

# 10. Entidades conceptuales

La jerarquía principal será:

```text
Organization
   │
   ├── Members
   │
   └── Companies
          │
          ├── AI Agents
          ├── Knowledge
          ├── Conversations
          ├── Leads
          └── Integrations
```

Una organización puede eventualmente gestionar más de una empresa o marca.

---

# 11. Funcionalidades del MVP

El MVP debe demostrar cinco capacidades principales.

## 11.1 Empresas

Permitir:

* crear empresa;
* editar empresa;
* registrar website;
* almacenar información básica;
* asociar empresa a una organización.

Información:

```text
name
legal_name
website
description
industry
country
timezone
contact information
brand information
```

---

## 11.2 Knowledge Base

Permitir fuentes:

### Iniciales

* website;
* URL;
* texto manual;
* PDF.

Cada fuente debe mostrar estado:

```text
pending
processing
ready
failed
```

Debe ser posible:

* añadir;
* procesar;
* reindexar;
* desactivar;
* eliminar.

---

## 11.3 AI Agent

Cada empresa podrá tener al menos un agente.

Configuración:

```text
name
role
description
objective
tone
language
system instructions
fallback behavior
model
status
```

Estados:

```text
draft
active
disabled
```

---

## 11.4 Chat

Permitir conversar con un agente.

Debe:

* mantener conversation_id;
* almacenar mensajes;
* recuperar conocimiento mediante RAG;
* generar respuestas con Gemini;
* detectar falta de información;
* conservar aislamiento tenant.

---

## 11.5 Leads

Detectar intención comercial.

Permitir capturar:

* nombre;
* teléfono;
* email;
* interés;
* conversación origen;
* estado.

Estados previstos:

```text
new
qualified
contacted
converted
lost
```

---

# 12. Flujo de creación de empresa

## Paso 1

Usuario selecciona:

```text
New Company
```

## Paso 2

Introduce:

```text
Company name
Website
Industry opcional
```

## Paso 3

Sistema registra empresa.

## Paso 4

Sistema comienza ingestión del website.

## Paso 5

Contenido se normaliza.

## Paso 6

Gemini puede generar un perfil estructurado.

Ejemplo:

```json
{
  "company_name": "",
  "industry": "",
  "description": "",
  "products": [],
  "services": [],
  "locations": [],
  "contact_information": {},
  "opening_hours": [],
  "faq": [],
  "policies": []
}
```

## Paso 7

Usuario revisa y corrige información detectada.

Nunca asumir que la extracción automática es perfecta.

---

# 13. Pipeline de ingestión

Arquitectura:

```text
URL / File / Text
        ↓
Extractor
        ↓
Normalized Document
        ↓
Chunking
        ↓
Metadata
        ↓
Gemini Embedding
        ↓
pgvector
```

---

# 14. Chunking

Los documentos no deben guardarse únicamente como bloques gigantes.

Crear unidades semánticas.

Configuración inicial orientativa:

```text
500–1000 tokens por chunk
```

con pequeño overlap cuando corresponda.

El algoritmo debe poder ajustarse posteriormente.

Cada chunk debe conservar metadata de origen.

Ejemplo:

```json
{
  "source_type": "website",
  "source_url": "https://empresa.com/servicios",
  "title": "Servicios",
  "indexed_at": "...",
  "language": "es"
}
```

---

# 15. RAG

RAG será la estrategia principal para personalizar conocimiento.

No se realizará fine-tuning en el MVP.

Flujo:

```text
User Question
      ↓
Embedding
      ↓
Vector search
      ↓
Tenant filter
      ↓
Relevant chunks
      ↓
Prompt context
      ↓
Gemini
      ↓
Answer
```

Búsqueda vectorial obligatoriamente filtrada por:

```text
organization_id
company_id
```

Opcionalmente:

```text
agent_id
source_id
```

---

# 16. Estrategia de respuesta

Prompt conceptual:

```text
SYSTEM

You are the AI assistant for {company_name}.

ROLE
{role}

OBJECTIVE
{objective}

RULES
{agent_instructions}

KNOWLEDGE CONTEXT
{retrieved_chunks}

CONVERSATION
{history}

USER
{message}
```

El conocimiento externo no debe modificar instrucciones del sistema.

---

# 17. Seguridad frente a prompt injection

Contenido indexado puede contener textos como:

```text
Ignore all previous instructions.
```

Esos textos deben considerarse datos.

No instrucciones.

El sistema debe mantener una separación clara entre:

```text
SYSTEM INSTRUCTIONS
```

y:

```text
RETRIEVED KNOWLEDGE
```

---

# 18. Perfil empresarial estructurado

Además del RAG, se almacenará información estructurada de la empresa.

Ejemplos:

```text
services
products
locations
contact_channels
business_hours
FAQs
policies
```

Esto permite responder consultas simples sin depender exclusivamente de búsqueda vectorial y facilitar integraciones posteriores.

---

# 19. Conversaciones

Entidad:

```text
conversations
```

Debe almacenar:

```text
id
organization_id
company_id
agent_id
visitor_id
channel
status
started_at
last_message_at
```

Entidad:

```text
messages
```

Debe almacenar:

```text
id
conversation_id
role
content
created_at
metadata
```

Roles:

```text
user
assistant
system
tool
```

---

# 20. Lead detection

Inicialmente puede utilizar Gemini para clasificación estructurada.

Ejemplo conceptual:

```json
{
  "is_lead": true,
  "intent": "request_quote",
  "confidence": 0.91,
  "missing_fields": ["email"]
}
```

No realizar otra llamada al modelo si puede obtenerse el mismo resultado de forma fiable durante la respuesta principal.

La optimización de costes es parte de la arquitectura.

---

# 21. Herramientas del agente

El diseño debe prever function/tool calling.

Tools futuros:

```text
search_knowledge
create_lead
get_locations
get_products
get_services
get_availability
request_appointment
send_email
create_crm_contact
call_webhook
```

Una tool debe estar expresamente habilitada para un agente antes de poder utilizarse.

No permitir ejecución arbitraria.

---

# 22. Integraciones

## MVP

No es obligatorio implementar integraciones empresariales externas en las primeras fases.

Debe prepararse la arquitectura.

## Prioridad posterior

1. Webhook genérico
2. Google Calendar
3. Email
4. WhatsApp
5. CRM
6. ERP

Posteriormente:

* HubSpot;
* Salesforce;
* SAP;
* Odoo;
* servicios personalizados.

---

# 23. Dashboard

Navegación prevista:

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

---

# 24. Overview

Mostrar progresivamente:

```text
Total conversations
Leads generated
Conversion rate
Resolution rate
Human escalations
Knowledge sources
AI usage
```

El MVP puede comenzar con métricas básicas.

---

# 25. Knowledge UI

Ejemplo conceptual:

```text
KNOWLEDGE BASE

Website
empresa.com
43 pages
READY

Documents
catalogo.pdf
READY

Manual Knowledge
Promoción septiembre
READY

[ Add source ]
```

---

# 26. AI Agent UI

Ejemplo:

```text
Agent name
[ Ava ]

Role
[ Sales Assistant ]

Objective
[ Convert qualified visitors into leads ]

Tone
[ Professional ]

Language
[ Spanish ]

Model
[ Gemini ]

Instructions
[ .................................... ]

[ Save ]
[ Test Agent ]
```

---

# 27. Conversation UI

Permitir visualizar:

* usuario;
* agente;
* timestamps;
* origen;
* lead detectado;
* errores;
* escalamiento.

---

# 28. Analytics

Objetivo posterior:

```text
Conversations
Unique users
Leads
Conversions
Top questions
Unanswered questions
Knowledge gaps
Token/API usage
Average response time
```

Especialmente importante:

```text
Unanswered questions
```

debe permitir identificar información que el negocio debería añadir a su Knowledge Base.

---

# 29. Widget web

Fase posterior del MVP:

Generar un widget insertable.

Objetivo conceptual:

```html
<script
  src="https://ai.form4th.com/widget.js"
  data-agent="PUBLIC_AGENT_ID">
</script>
```

No colocar información privada dentro del script.

El ID público no debe servir para acceder directamente a recursos administrativos.

---

# 30. Fases de desarrollo

## FASE 1 — Foundation

Objetivo:

crear la base profesional del proyecto.

Incluye:

* estructura monorepo;
* frontend Next.js;
* backend FastAPI;
* configuración;
* `.env.example`;
* conexión Supabase;
* SQLAlchemy;
* Alembic;
* health checks;
* Gemini service;
* tests básicos;
* Docker backend;
* documentación.

Resultado:

```text
Frontend → Backend → Gemini
                  → Supabase
```

debe estar operativo.

NO desarrollar todavía el RAG completo.

---

## FASE 2 — Multi-tenancy y Companies

Incluye:

* authentication;
* organizations;
* users/members;
* companies;
* authorization;
* RLS cuando corresponda;
* CRUD empresa;
* UI empresas.

Resultado:

un usuario autenticado puede administrar una empresa dentro de su organización.

---

## FASE 3 — Knowledge Ingestion

Incluye:

* knowledge_sources;
* documents;
* website ingestion;
* manual text;
* PDF;
* normalización;
* chunking;
* estados de procesamiento;
* reindexación.

Resultado:

la plataforma puede convertir fuentes empresariales en chunks procesables.

---

## FASE 4 — Embeddings + RAG

Incluye:

* pgvector;
* `gemini-embedding-2`;
* embeddings 768 dimensiones inicialmente;
* vector search;
* metadata;
* retrieval;
* tenant filters;
* relevancia;
* tests de aislamiento.

Resultado:

una pregunta puede recuperar conocimiento empresarial relevante.

---

## FASE 5 — AI Agent + Chat

Incluye:

* ai_agents;
* instructions;
* Gemini chat;
* RAG context;
* conversaciones;
* mensajes;
* interfaz de prueba;
* fallback;
* protección básica contra prompt injection.

Resultado:

un administrador puede configurar y probar un agente personalizado.

---

## FASE 6 — Leads

Incluye:

* intent detection;
* leads;
* lead qualification;
* conversation → lead;
* UI leads;
* estados.

Resultado:

el agente puede transformar una conversación comercial en un lead almacenado.

---

## FASE 7 — Analytics

Incluye:

* métricas;
* dashboard;
* preguntas frecuentes;
* knowledge gaps;
* uso de IA;
* rendimiento.

---

## FASE 8 — Widget

Incluye:

* agente público;
* widget;
* session handling;
* rate limiting;
* CORS;
* configuración visual básica.

Resultado:

una empresa puede incorporar el agente en su página.

---

## FASE 9 — Integrations

Prioridad:

```text
Webhook
Calendar
Email
WhatsApp
CRM
ERP
```

No desarrollar todas simultáneamente.

---

# 31. Lo que NO forma parte del MVP

No desarrollar inicialmente:

* modelo fundacional propio;
* entrenamiento desde cero;
* fine-tuning;
* Kubernetes;
* microservicios distribuidos;
* aplicación móvil nativa;
* avatar 3D;
* clonación de voz;
* llamadas telefónicas IA;
* generación de video;
* marketplace;
* 20 integraciones;
* ERP propio;
* CRM completo.

Estos elementos pueden formar parte del roadmap futuro.

---

# 32. Principios del producto

## Configurable

Una empresa nueva no debe requerir modificar código.

## Multiempresa

El núcleo debe poder atender múltiples clientes.

## Seguro

Los tenants deben permanecer aislados.

## Basado en conocimiento real

El agente debe priorizar información proporcionada por la empresa.

## Extensible

Proveedores de IA, crawlers e integraciones deben poder sustituirse.

## Medible

Las acciones del agente deben generar métricas.

## Comercialmente útil

El objetivo no es demostrar que Gemini puede conversar.

El objetivo es resolver procesos reales.

---

# 33. Criterio de éxito del MVP

El MVP se considerará funcional cuando pueda demostrarse este flujo completo:

```text
1. Crear cuenta

2. Crear organización

3. Crear empresa

4. Registrar website

5. Extraer información

6. Agregar documento

7. Generar embeddings

8. Almacenar conocimiento

9. Configurar agente

10. Preguntar por información empresarial

11. Recuperar contexto correcto

12. Gemini responder basándose en contexto

13. Registrar conversación

14. Detectar intención comercial

15. Crear lead

16. Consultar resultados desde dashboard
```

---

# 34. Ejemplo de funcionamiento esperado

Empresa:

```text
Aventura Gym
```

Conocimiento:

```text
sedes
horarios
planes
promociones
servicios
preguntas frecuentes
```

Usuario:

```text
¿Tienen una sede cerca de San Martín de Porres?
```

Sistema:

```text
Pregunta
↓
Embedding
↓
RAG
↓
Sedes relevantes
↓
Gemini
```

Respuesta:

Debe utilizar exclusivamente las ubicaciones y datos disponibles.

Posteriormente:

```text
Usuario:
Quiero conocer la sede mañana.

Agente:
Puede iniciar el flujo correspondiente.

Lead:
Creado.
```

El mismo software debe posteriormente aceptar:

```text
Clínica
Estudio legal
Inmobiliaria
Gimnasio
Constructora
Consultora
```

sin modificar el núcleo.

---

# 35. Resultado estratégico

FORM4TH AI Agent debe evolucionar hacia:

```text
                        FORM4TH
                       AI PLATFORM
                           │
             ┌─────────────┼─────────────┐
             │             │             │
          Cliente A     Cliente B     Cliente C
             │             │             │
           Agent         Agent         Agent
             │             │             │
       ┌─────┼─────┐ ┌─────┼─────┐ ┌─────┼─────┐
       │     │     │ │     │     │ │     │     │
      RAG  Tools Leads RAG Tools Leads RAG Tools Leads
```

No crear implementaciones aisladas por cliente.

El valor del producto está en que FORM4TH pueda configurar y desplegar nuevos agentes empresariales sin reprogramar la plataforma.
