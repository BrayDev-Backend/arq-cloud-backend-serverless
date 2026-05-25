# ADR'S 

| Campo del ADR          | Descripcion |
|------------------------|-------------|
| Titulo                 |Uso de Azure Functions (Consumption Plan) sobre Azure App Service para la logica de negocio de RapidGo             |
| Contexto               |RapidGo requiere un backend que escale               |
| Alternativas evaluadas |             |
| Decision               |             |
| Consecuencias          |             |

| Campo         | Contenido |
|---------------|-----------|
| **Título**    | Uso de Azure Functions (Consumption Plan) sobre Azure App Service para la lógica de negocio de RapidGo. |
| **Contexto**  | RapidGo necesita escalar automáticamente hasta 500 req/seg en picos (días festivos) sin intervención manual. Actualmente el monolito Node.js se satura en horas pico (12m-2pm, 6pm-9pm) con respuestas >8 segundos y 12% de cancelaciones. El servidor dedicado cuesta $4.200.000 COP/mes fijos, con CPU al 4% en madrugada. Presupuesto piloto <$50 USD/mes, equipo con experiencia en Node.js/Python, infraestructura de una sola persona. |
| **Alternativas evaluadas** | 1) **Azure App Service (Premium/Isolated)** : autoescalado, familiar, zero-downtime, pero costo fijo mensual (>$75 USD) y administración manual. 2) **Azure Functions Consumption Plan**: escala de 0 a N en ms, pago por ejecución (1M gratis/mes), Node.js/Python, zero-downtime. Desventaja: posible cold start. |
| **Decisión**  | Se elige **Azure Functions Consumption Plan**. Cumple escalabilidad automática (500 req/seg), pago por uso (elimina costo fijo), zero-downtime y baja carga operativa. Cold start aceptable para <800ms P95. Alineado con arquitectura de referencia serverless de Microsoft. |
