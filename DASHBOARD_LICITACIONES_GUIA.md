# 📄 Dashboard de Licitaciones 2026 - Guía Completa

## 🎯 Resumen de Cambios Implementados

### 1. **Optimización del Código**
- ✅ Eliminación de etiquetas HTML innecesarias y código comentado
- ✅ Estructura modular con funciones bien definidas
- ✅ Mejora en la legibilidad y mantenibilidad del código
- ✅ Uso eficiente de caché de Streamlit para optimizar rendimiento

### 2. **Filtro de Vista Semanal 2026**
- ✅ **4 opciones de visualización:**
  - Todas las Licitaciones
  - Esta Semana (Lunes a Domingo actual)
  - Próxima Semana (Lunes a Domingo siguiente)
  - Esta Semana + Próxima Semana (14 días)
- ✅ Cálculo automático de rangos de fechas basado en la fecha actual
- ✅ Indicadores visuales de las fechas seleccionadas
- ✅ Filtrado inteligente basado en la "Fecha Clave" (fecha más cercana de cada licitación)

### 3. **Reporte Semanal Consolidado**
- ✅ **Generación automática de reportes HTML profesionales** que incluyen:
  - Header con gradiente corporativo
  - Estadísticas resumidas (KPIs)
  - Tabla de licitaciones de esta semana
  - Tabla de licitaciones de próxima semana
  - Formato responsive y profesional
  - Estilos CSS inline para compatibilidad con clientes de correo

### 4. **Sistema de Envío de Correos Masivos**
- ✅ **Integración completa con Outlook** (smtp.office365.com)
- ✅ **16 usuarios preconfigurados** con sus correos corporativos
- ✅ Envío personalizado (cada correo incluye el nombre del destinatario)
- ✅ Barra de progreso en tiempo real
- ✅ Manejo de errores robusto con reporte de fallos
- ✅ Formato HTML optimizado para clientes de correo

### 5. **Mejoras Visuales y UX**
- ✅ Header rediseñado con gradientes modernos
- ✅ KPIs ejecutivos con métricas clave
- ✅ Comparativa visual entre semana actual y próxima (gráficos de pie)
- ✅ Tabla de datos ordenada por urgencia (fecha clave)
- ✅ Análisis Lean/OKR mantenido y optimizado
- ✅ Footer informativo con timestamp

---

## 📋 Funcionalidades Principales

### **A. Filtros Inteligentes**

1. **Filtro Semanal Principal:**
   - Selector dropdown con 4 opciones
   - Cálculo automático de semanas (lunes a domingo)
   - Indicador visual de rango de fechas

2. **Filtros Adicionales (Cascada):**
   - Estado de licitación
   - Usuario responsable
   - Unidad organizacional
   - Los filtros se actualizan dinámicamente

### **B. KPIs y Métricas**

**Panel Principal:**
- 📋 Total Licitaciones (con % del total)
- 💰 Monto Estimado (con % del total)
- 📦 Total Items
- ⚠️ Estados Críticos

**Comparativa Semanal:**
- Licitaciones esta semana vs próxima semana
- Montos totales comparados
- Distribución por estado (gráficos de pie)

### **C. Sistema de Correos**

**Características:**
- Envío masivo a 16 usuarios predefinidos
- HTML profesional con diseño responsive
- Personalización por destinatario
- Reporte consolidado con:
  - Estadísticas generales
  - Tabla de licitaciones esta semana
  - Tabla de licitaciones próxima semana
  - Montos y conteos

**Configuración Requerida:**
1. Correo corporativo Outlook
2. Contraseña de aplicación (no la contraseña normal)
3. Clic en botón "Enviar Reporte Semanal"

---

## 👥 Usuarios Configurados

```
1.  Rubén Uribe - ruben.uribe@redsalud.gob.cl
2.  Lesly Andrea Díaz Aburto - lesly.diaz@redsalud.gob.cl
3.  JACQUELINE OYARZUN ALVAREZ - jacqueline.oyarzuna@redsalud.gob.cl
4.  Cecilia Garay Lemuy - cecilia.garay@redsalud.gob.cl
5.  Alicia Vidal Paredes - alicia.vidal@redsalud.gob.cl
6.  JUAN FELIPE ROJEL HUENTRO - juan.rojel@redsalud.gob.cl
7.  Ivan Vargas Ojeda - ivan.vargas@redsalud.gob.cl
8.  PAULINA NICOLE LONCOPAN CARRILLO - paulina.loncopan@redsalud.gob.cl
9.  Ariela Acevedo - ariela.ariela@redsalud.gob.cl
10. Jonathan Salvo Currin - jonathan.salvo@redsalud.gob.cl
11. ALEJANDRA NICOLE ALMONACID LEVINIERE - alejandra.almonacid@redsalud.gob.cl
12. RODRIGO ALEJANDRO LABRIN ESCALONA - rodrigo.labrin@redsalud.gob.cl
13. Bastian Miranda Coronado - bastian.miranda@redsalud.gob.cl
14. NICOLAS ASENCIO MOREIRA - nicolas.asencio@redsalud.gob.cl
15. Verónica Aracely Márquez Aguila - verónica.márqueza@redsalud.gob.cl
16. Rosa Vasquez - rosa.vasquez@redsalud.gob.cl
```

---

## 🚀 Cómo Usar el Dashboard

### **Paso 1: Acceder al Dashboard**
```bash
# Si Streamlit ya está corriendo, navega a la página
# Si no, ejecuta:
python -m streamlit run main.py
```

### **Paso 2: Seleccionar Vista Semanal**
1. En el selector "Seleccionar Vista", elige:
   - **"Esta Semana"** para ver solo licitaciones de esta semana
   - **"Próxima Semana"** para planificar la siguiente semana
   - **"Esta Semana + Próxima Semana"** para vista completa de 14 días
   - **"Todas las Licitaciones"** para vista sin filtro temporal

### **Paso 3: Aplicar Filtros Adicionales (Opcional)**
- Filtra por Estado, Usuario o Unidad según necesites
- Los filtros son acumulativos

### **Paso 4: Analizar Datos**
- Revisa los KPIs en la parte superior
- Compara esta semana vs próxima semana en los gráficos
- Explora la tabla detallada (expandible)

### **Paso 5: Enviar Reportes (Opcional)**
1. Expande "⚙️ Configuración de Correo"
2. Ingresa tu correo corporativo Outlook
3. Ingresa tu contraseña de aplicación
4. Clic en "📧 Enviar Reporte Semanal a Todos los Usuarios"
5. Espera la confirmación (barra de progreso)

---

## 🔐 Configuración de Contraseña de Aplicación Outlook

Para enviar correos desde Outlook, necesitas una **Contraseña de Aplicación**:

### **Pasos para Obtenerla:**

1. **Ir a tu cuenta Microsoft:**
   - Visita: https://account.microsoft.com/security

2. **Activar verificación en dos pasos:**
   - Si no está activada, actívala primero

3. **Crear contraseña de aplicación:**
   - Busca "Contraseñas de aplicación"
   - Clic en "Crear nueva contraseña de aplicación"
   - Copia la contraseña generada (16 caracteres)

4. **Usar en el Dashboard:**
   - Pega esta contraseña en el campo "Contraseña de Aplicación"
   - NO uses tu contraseña normal de Outlook

---

## 📊 Estructura del Reporte HTML

El correo enviado incluye:

```
┌─────────────────────────────────────┐
│  HEADER (Gradiente Azul)           │
│  - Título del reporte               │
│  - Fecha de generación              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  SALUDO PERSONALIZADO               │
│  Estimado/a [Nombre]                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  KPIs RESUMEN                       │
│  [Esta Semana] [Próxima] [Total]    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  TABLA: ESTA SEMANA                 │
│  Código | Nombre | Estado | Monto   │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  TABLA: PRÓXIMA SEMANA              │
│  Código | Nombre | Estado | Monto   │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  FOOTER                             │
│  Dirección de Abastecimiento        │
└─────────────────────────────────────┘
```

---

## 🛠️ Solución de Problemas

### **Problema: No se cargan los datos**
**Solución:**
- Verifica que existan los archivos CSV en `api/LI_DSSO/MAESTROS/`
- Ejecuta el actualizador de datos primero

### **Problema: Error al enviar correos**
**Soluciones:**
1. Verifica que uses una contraseña de aplicación (no tu contraseña normal)
2. Confirma que tu correo sea de Outlook/Office365
3. Revisa tu conexión a internet
4. Verifica que no haya firewall bloqueando el puerto 587

### **Problema: No aparecen licitaciones en vista semanal**
**Solución:**
- Verifica que las fechas de las licitaciones estén en el rango seleccionado
- Prueba con "Todas las Licitaciones" para ver si hay datos
- Revisa que las columnas de fecha estén correctamente formateadas

### **Problema: Los filtros no funcionan**
**Solución:**
- Limpia los filtros y vuelve a aplicarlos
- Recarga la página (F5)
- Verifica que los datos tengan las columnas Estado, C_Usuario, C_Unidad

---

## 📈 Análisis Lean/OKR

El dashboard incluye análisis avanzado:

### **OKR 1: Agilidad del Proceso**
- **Métrica:** Lead Time Promedio
- **Objetivo:** Reducir tiempo total del proceso
- **Cálculo:** Días desde Creación hasta Inicio de Contrato

### **OKR 2: Eficacia de Licitación**
- **Métrica:** Tasa de Adjudicación
- **Objetivo:** 85% de licitaciones adjudicadas
- **Cálculo:** (Adjudicadas / Total) × 100

### **OKR 3: Eficiencia Administrativa**
- **Métrica:** Valor por Item
- **Objetivo:** Maximizar valor por esfuerzo
- **Cálculo:** Monto Total / Cantidad de Items

---

## 🎨 Personalización

### **Agregar/Quitar Usuarios:**
Edita el diccionario `USUARIOS_CORREOS` en línea 64:

```python
USUARIOS_CORREOS = {
    "Nombre Completo": "correo@redsalud.gob.cl",
    # Agrega más usuarios aquí
}
```

### **Cambiar Diseño del Correo:**
Edita la función `generar_html_reporte()` (línea 104) para modificar:
- Colores (cambiar valores hexadecimales)
- Estructura de tablas
- Contenido del mensaje

### **Modificar Rango Semanal:**
Las funciones `obtener_semana_actual()` y `obtener_proxima_semana()` (líneas 83-95) calculan automáticamente las semanas. Puedes modificarlas si necesitas otro criterio.

---

## 📝 Notas Técnicas

### **Dependencias Requeridas:**
```python
streamlit
pandas
numpy
plotly
smtplib (incluido en Python)
email (incluido en Python)
```

### **Archivos Relacionados:**
- `api/LI_data_loader.py` - Carga de datos
- `style/style.css` - Estilos CSS (opcional)
- `api/LI_DSSO/MAESTROS/Maestro_Resumen.csv` - Datos principales
- `api/LI_DSSO/MAESTROS/Maestro_Detalle.csv` - Datos de items

### **Rendimiento:**
- Uso de `@st.cache_data` para optimizar carga
- Procesamiento eficiente de DataFrames con pandas
- Envío de correos con pausa de 2 segundos entre cada uno (evitar spam)

---

## ✅ Checklist de Implementación

- [x] Código optimizado sin HTML innecesario
- [x] Filtro de vista semanal (4 opciones)
- [x] Reporte consolidado HTML profesional
- [x] Sistema de envío masivo de correos
- [x] 16 usuarios configurados
- [x] Integración con Outlook
- [x] KPIs ejecutivos
- [x] Comparativa semanal visual
- [x] Análisis Lean/OKR
- [x] Manejo de errores robusto
- [x] Documentación completa

---

## 🎯 Próximos Pasos Sugeridos

1. **Probar el envío de correos** con tu cuenta corporativa
2. **Validar que todos los usuarios reciban los correos**
3. **Ajustar el diseño HTML** según preferencias de la jefatura
4. **Programar envíos automáticos** (opcional, requiere scheduler)
5. **Agregar exportación a PDF** del reporte (opcional)

---

## 📞 Soporte

Para modificaciones o problemas:
1. Revisa esta guía primero
2. Verifica los logs de Streamlit en la consola
3. Prueba con datos de ejemplo
4. Documenta el error específico

---

**Desarrollado para:** Red de Salud - Dirección de Abastecimiento  
**Versión:** 2.0 (2026)  
**Última actualización:** Febrero 2026
