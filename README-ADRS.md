# ADR'S 

| Campo         | Contenido |
|---------------|-----------|
| **Título**    | Uso de Azure Functions (Consumption Plan) sobre Azure App Service para la lógica de negocio de RapidGo. |
| **Contexto**  | RapidGo necesita escalar automáticamente hasta 500 req/seg en picos (días festivos) sin intervención manual.<br>Actualmente el monolito Node.js se satura en horas pico (12m-2pm, 6pm-9pm) con respuestas >8 segundos y 12% de cancelaciones.<br>El servidor dedicado cuesta $4.200.000 COP/mes fijos, con CPU al 4% en madrugada.<br>Presupuesto piloto <$50 USD/mes, equipo con experiencia en Node.js/Python, infraestructura de una sola persona. |
| **Alternativas evaluadas** | 1) **Azure App Service (Premium/Isolated)** : autoescalado, familiar, zero-downtime, pero costo fijo mensual (>$75 USD) y administración manual.<br>2) **Azure Functions Consumption Plan**: escala de 0 a N en ms, pago por ejecución (1M gratis/mes), Node.js/Python, zero-downtime. Desventaja: posible cold start. |
| **Decisión**  | Se elige **Azure Functions Consumption Plan**.<br>Cumple escalabilidad automática (500 req/seg), pago por uso (elimina costo fijo), zero-downtime y baja carga operativa.<br>Cold start aceptable para <800ms P95. Alineado con arquitectura de referencia serverless de Microsoft. |

| Campo | Contenido |
|-------|-----------|
| **Título** | Adopción de Cosmos DB (NoSQL) en lugar de Azure SQL Database para persistencia de pedidos, usuarios y estados de entrega. |
| **Contexto** | RapidGo actualmente usa MySQL (3 años de datos).<br>Requiere latencia <800ms P95, escalar a 500 req/seg, atributos variables por tipo de negocio.<br>Presupuesto <$50 USD/mes, datos en Brazil South o East US, mínima administración.<br>Se permite cambio de paradigma a NoSQL con justificación. |
| **Alternativas evaluadas** | 1) **Azure SQL Database (Serverless/Basic)**: compatible con MySQL, ACID, free tier 32 GB.<br>Desventajas: escalado horizontal complejo, latencia mayor bajo carga, esquema rígido para atributos variables.<br>2) **Cosmos DB (Core API)**: escalado horizontal automático (RU/s), latencia <10ms, esquema flexible, free tier 1000 RU/s + 25 GB, Change Feed para notificaciones.<br>Desventaja: cambio de paradigma relacional a documento. |
| **Decisión** | Se elige **Cosmos DB** por su escalabilidad, latencia y flexibilidad de esquema necesarios para cumplir 500 req/seg y <800ms P95.<br>El free tier respeta el presupuesto.<br>Change Feed permite notificaciones confiables.<br>Se justifica el cambio de paradigma por la naturaleza polimórfica de los pedidos y la necesidad de escalar sin intervención manual. |

| Campo | Contenido |
|-------|-----------|
| **Título** | Implementación de Azure API Management (Developer tier) como gateway unificado para exponer las Azure Functions. |
| **Contexto** | RapidGo requiere punto único de entrada con autenticación JWT (reemplazar implementación artesanal actual).<br>También necesita throttling por usuario, versionado de API, y compatibilidad con endpoints existentes (mismas rutas/JSON).<br>Carga operativa mínima (equipo de una persona). |
| **Alternativas evaluadas** | 1) **Exposición directa + Easy Auth**: sin costo adicional, pero sin throttling, ni versionado, ni transformación. La gestión JWT quedaría dispersa.<br>2) **API Management Developer tier**: centraliza JWT, rate limiting, reescritura de URLs, caché, portal de desarrollador. Costo ~$50 USD/mes (dentro del presupuesto). |
| **Decisión** | Se elige **API Management** porque elimina deuda técnica de autenticación.<br>Permite throttling para proteger el consumo de Functions/Cosmos.<br>Facilita compatibilidad backward con endpoints existentes.<br>El costo fijo se compensa con ahorro operativo (una persona administra el gateway). Alineado con arquitectura de referencia Microsoft. |

| Campo | Contenido |
|-------|-----------|
| **Título** | Uso de Azure Blob Storage (LRS Standard) sobre Azure Files para almacenar comprobantes de entrega, imágenes de productos y reportes. |
| **Contexto** | RapidGo necesita almacenar fotos (subidas por repartidores), imágenes de productos y exports de reportes.<br>Acceso: escritura única, lectura ocasional desde app móvil o panel admin.<br>Presupuesto bajo, minimizar costos. |
| **Alternativas evaluadas** | 1) **Azure Files (Standard LRS)**: protocolo SMB/NFS, montable como unidad. Más caro por GB (~$0.06 vs $0.02), mayor latencia para app móvil.<br>2) **Blob Storage (LRS Standard)**: costo menor, URL directa para imágenes, integración con CDN, SAS tokens.<br>Desventaja: no es sistema de archivos montable (acceso vía SDK). |
| **Decisión** | Se elige **Blob Storage** porque el caso de uso principal es almacenar y servir archivos no estructurados a clientes móviles (imágenes).<br>Costo inferior respeta presupuesto piloto.<br>Las Functions usan SDK sin fricción.<br>Servicio estándar en arquitecturas serverless para contenido estático. |

| Campo | Contenido |
|-------|-----------|
| **Título** | Implementación de Azure Notification Hubs (Free tier) sobre Azure Communication Services para el envío de notificaciones push a clientes y repartidores. |
| **Contexto** | RapidGo debe mejorar tasa de entrega del 67% actual a >95%, integrando directamente con FCM (Android) y APNs (iOS).<br>Notificaciones por cambio de estado del pedido.<br>Presupuesto piloto limitado, equipo de una persona. |
| **Alternativas evaluadas** | 1) **Azure Communication Services (ACS) – Push**: moderno, SDK unificados, pero sin free tier para push (~$0.005/notificación).<br>Para 1.200 pedidos/día (108.000 notificaciones/mes) excede $50 USD.<br>2) **Notification Hubs (Free tier)**: 1M notificaciones/mes gratis, manejo automático de registros por plataforma, retries, telemetría.<br>Desventaja: SDKs menos modernos (pero soporta REST). |
| **Decisión** | Se elige **Notification Hubs** porque su free tier se ajusta perfectamente al volumen de RapidGo (108.000 notificaciones/mes), permitiendo cumplir >95% de entrega sin costo adicional.<br>Telemetría integrada ayuda al monitoreo.<br>Es el componente estándar en arquitectura serverless de Microsoft. |
