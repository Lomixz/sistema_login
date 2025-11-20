# Asignación Masiva de Materias - Guía Completa

## Descripción General

El módulo de **Asignación Masiva de Materias** permite asignar materias a múltiples profesores de forma eficiente, ahorrando tiempo significativo especialmente cuando se manejan decenas o cientos de profesores y materias.

## Características Principales

### 1. Interfaz de Matriz Visual
- Matriz interactiva profesor × materia
- Checkboxes para seleccionar/deseleccionar asignaciones
- Indicadores visuales de carga de trabajo por profesor
- Colores para identificar rápidamente el estado de cada profesor

### 2. Herramientas de Selección Rápida
- **Seleccionar Todo**: Asigna todas las materias visibles a todos los profesores
- **Limpiar Selección**: Desasigna todo
- **Invertir Selección**: Invierte el estado actual
- **Seleccionar Fila**: Asigna todas las materias a un profesor específico
- **Seleccionar Columna**: Asigna una materia a todos los profesores

### 3. Importación Masiva desde CSV
- Carga cientos de asignaciones con un solo archivo
- Validación automática de datos
- Reportes detallados de éxitos y errores

### 4. Auto-Asignación Inteligente
- Distribuye automáticamente materias entre profesores disponibles
- Considera la carga actual de cada profesor
- Prioriza profesores de tiempo completo

### 5. Indicadores de Carga de Trabajo
- Visualización de horas actuales vs. límite máximo
- Barras de progreso con código de colores
- Estados: Sin carga, Baja, Adecuada, Alta, Sobrecarga

### 6. Filtros Avanzados
- Por carrera
- Por cuatrimestre
- Solo profesores con capacidad disponible

## Casos de Uso

### Caso 1: Asignación Manual Selectiva

**Escenario**: Tienes 20 profesores y 50 materias, necesitas asignar algunas materias específicas.

**Pasos**:
1. Accede a **Admin** → **Asignación Masiva de Materias**
2. Aplica filtros si necesitas trabajar con un subconjunto (ej: solo Cuatrimestre 1)
3. Haz clic en los checkboxes de las combinaciones profesor-materia deseadas
4. Usa los botones de selección de fila/columna para agilizar
5. Haz clic en **Guardar Cambios**

**Tiempo estimado**: 5-10 minutos

### Caso 2: Importación Masiva desde CSV

**Escenario**: Nuevo ciclo escolar con 100 profesores y 200 materias. Ya tienes la información en Excel.

**Pasos**:
1. Haz clic en **Importar desde CSV**
2. Descarga la **Plantilla CSV**
3. Completa el CSV con el formato:
   ```csv
   profesor_email,materia_codigo
   juan.perez@uni.edu,MAT-101
   juan.perez@uni.edu,MAT-201
   maria.garcia@uni.edu,FIS-101
   ```
4. Sube el archivo
5. Revisa el reporte de resultados

**Tiempo estimado**: 15-20 minutos (incluyendo preparación del CSV)

### Caso 3: Duplicar Ciclo Anterior

**Escenario**: El nuevo ciclo tiene la misma estructura que el anterior, solo algunos cambios menores.

**Pasos**:
1. En la página de Asignación Masiva, haz clic en **Exportar Actuales**
2. Se descargará un CSV con todas las asignaciones actuales
3. Abre el CSV en Excel y realiza los ajustes necesarios:
   - Elimina filas de profesores que ya no están
   - Agrega nuevas asignaciones
   - Modifica asignaciones existentes
4. Guarda el CSV
5. Haz clic en **Importar desde CSV** y sube el archivo modificado

**Tiempo estimado**: 10-15 minutos

### Caso 4: Auto-Asignación por Carrera

**Escenario**: Carrera nueva con 30 profesores y 80 materias. Quieres una distribución equitativa automática.

**Pasos**:
1. Aplica el filtro de **Carrera** para seleccionar la carrera específica
2. Haz clic en **Auto-Asignar**
3. Confirma la acción
4. El sistema distribuirá automáticamente todas las materias entre los profesores disponibles
5. Revisa la distribución y realiza ajustes manuales si es necesario
6. Haz clic en **Guardar Cambios**

**Tiempo estimado**: 5 minutos + revisión

### Caso 5: Asignación por Cuatrimestre

**Escenario**: Necesitas asignar solo las materias del Cuatrimestre 3.

**Pasos**:
1. Aplica el filtro **Cuatrimestre = 3**
2. Opcionalmente, filtra también por **Carrera**
3. Usa las herramientas de selección rápida o importa un CSV
4. Guarda los cambios

**Tiempo estimado**: Según método (manual: 10-15 min, CSV: 5 min)

## Formato del Archivo CSV

### Estructura Básica

```csv
profesor_email,materia_codigo
profesor1@universidad.edu,MAT-101
profesor1@universidad.edu,MAT-201
profesor2@universidad.edu,FIS-101
profesor2@universidad.edu,FIS-102
profesor3@universidad.edu,QUI-101
```

### Reglas de Validación

1. **Primera fila**: Debe contener los encabezados `profesor_email,materia_codigo`
2. **Email del profesor**: Debe existir en el sistema y estar activo
3. **Código de materia**: Debe existir en el sistema y estar activa
4. **Formato**: CSV estándar con codificación UTF-8
5. **Duplicados**: Si una asignación ya existe, se omite sin error

### Ejemplo Real

```csv
profesor_email,materia_codigo
juan.perez@uni.edu,ING-SIS-101
juan.perez@uni.edu,ING-SIS-102
juan.perez@uni.edu,ING-SIS-103
maria.garcia@uni.edu,MAT-CALC-1
maria.garcia@uni.edu,MAT-CALC-2
carlos.lopez@uni.edu,FIS-MEC-1
carlos.lopez@uni.edu,FIS-MEC-2
ana.martinez@uni.edu,QUI-GEN-1
```

## Indicadores de Carga de Trabajo

### Límites por Tipo de Profesor

| Tipo de Profesor | Límite Recomendado | Límite Máximo |
|------------------|-------------------|---------------|
| Tiempo Completo  | 35 horas          | 40 horas (8h/día x 5 días) |
| Por Asignatura   | 15 horas          | 20 horas      |

### Códigos de Color

- **Gris (Sin carga)**: 0 horas asignadas
- **Azul (Baja)**: < 50% del límite recomendado
- **Verde (Adecuada)**: 50-100% del límite recomendado
- **Amarillo (Alta)**: 100% recomendado - límite máximo
- **Rojo (Sobrecarga)**: > límite máximo

### Interpretación

```
Profesor: Juan Pérez (TC)
[████████████░░░░] 30h / 40h
```

- Tiene 30 horas asignadas
- Límite máximo: 40 horas (8 horas/día x 5 días)
- Estado: Adecuado (verde)
- Puede recibir 10 horas más

## Funcionalidades Avanzadas

### 1. Filtro "Solo Profesores con Capacidad"

Cuando activas este filtro, solo se muestran profesores que aún tienen capacidad para más materias según su tipo y carga actual.

**Útil para**:
- Asignar materias nuevas sin sobrecargar a nadie
- Identificar rápidamente quién puede tomar más trabajo

### 2. Exportar Asignaciones Actuales

Genera un CSV con todas las asignaciones existentes. Este CSV puede ser:
- Editado y reimportado para hacer cambios masivos
- Usado como respaldo antes de hacer cambios grandes
- Compartido con otros administradores
- Usado como plantilla para el siguiente ciclo

### 3. Plantilla CSV de Ejemplo

Descarga un archivo CSV con el formato correcto y datos de ejemplo para que puedas ver exactamente cómo estructurar tu archivo.

### 4. Contador de Cambios en Tiempo Real

Mientras editas la matriz, un contador muestra cuántos cambios tienes pendientes de guardar. Esto incluye:
- Nuevas asignaciones
- Asignaciones eliminadas

### 5. Advertencia de Cambios sin Guardar

Si intentas salir de la página con cambios pendientes, el navegador te advertirá para evitar pérdida de datos.

## Mejores Prácticas

### 1. Usa Filtros para Trabajar por Partes

En lugar de ver 100 profesores y 200 materias a la vez:
- Filtra por carrera
- Trabaja por cuatrimestre
- Procesa en lotes manejables

### 2. Exporta Antes de Cambios Masivos

Siempre exporta las asignaciones actuales antes de hacer cambios grandes. Así tienes un punto de restauración.

### 3. Usa CSV para Grandes Volúmenes

Si necesitas asignar más de 50 materias, usa CSV en lugar de la interfaz manual:
- Más rápido
- Menos propenso a errores de clic
- Más fácil de auditar

### 4. Verifica la Carga de Trabajo

Después de asignar, revisa las barras de carga de cada profesor:
- Nadie en rojo (sobrecarga)
- Distribución equitativa
- Considera especialidades y preferencias

### 5. Guarda Frecuentemente

Si estás haciendo muchos cambios manuales, guarda cada cierto tiempo para no perder el progreso.

### 6. Aprovecha la Auto-Asignación

Para carreras nuevas o reestructuraciones completas:
1. Usa auto-asignación primero
2. Revisa la distribución
3. Ajusta manualmente lo necesario

## Solución de Problemas

### Problema: "No se encontró profesor con email X"

**Causas**:
- Email mal escrito en el CSV
- Profesor no existe en el sistema
- Profesor desactivado

**Solución**:
- Verifica el email en la gestión de profesores
- Corrige el CSV y vuelve a importar

### Problema: "No se encontró materia con código X"

**Causas**:
- Código mal escrito
- Materia no existe
- Materia inactiva

**Solución**:
- Verifica el código en la gestión de materias
- Corrige el CSV

### Problema: "Archivo CSV con columnas faltantes"

**Causa**: El CSV no tiene los encabezados correctos

**Solución**:
- Asegúrate de que la primera fila sea: `profesor_email,materia_codigo`
- Descarga la plantilla para ver el formato exacto

### Problema: Cambios no se guardan

**Causa**: No hiciste clic en "Guardar Cambios"

**Solución**:
- Siempre haz clic en el botón verde "Guardar Cambios" o "Guardar Todos los Cambios"
- Verifica el contador de cambios antes de salir

### Problema: Profesor aparece sobrecargado después de asignar

**Causa**: Ya tenía muchas horas asignadas previamente

**Solución**:
- Usa el filtro "Solo profesores con capacidad"
- Revisa las barras de carga antes de asignar
- Redistribuye materias si es necesario

## Shortcuts de Teclado (futuros)

Estos atajos están planeados para una futura actualización:

- `Ctrl + A`: Seleccionar todas
- `Ctrl + Shift + A`: Limpiar selección
- `Ctrl + I`: Invertir selección
- `Ctrl + S`: Guardar cambios

## Seguridad y Permisos

- ✅ Solo usuarios con rol **Administrador** pueden acceder
- ✅ Todas las operaciones se auditan en la base de datos
- ✅ Validaciones estrictas antes de guardar
- ✅ Transacciones: si hay error, nada se guarda
- ✅ Confirmación antes de auto-asignación masiva

## Limitaciones Conocidas

1. **Límite visual**: La matriz funciona bien hasta ~50 profesores × 100 materias. Para más, usa CSV.
2. **Sin validación de horarios**: El sistema no verifica conflictos de horarios al asignar (esto se hace en el módulo de horarios).
3. **Un profesor = múltiples materias**: No hay límite de materias por profesor, solo de horas.

## Comparación de Métodos

| Método | Velocidad | Mejor para | Dificultad |
|--------|-----------|------------|------------|
| **Manual en Matriz** | Media | Asignaciones específicas, < 50 materias | Baja |
| **Selección Rápida** | Media-Alta | Patrones simples (toda una fila/columna) | Baja |
| **Importar CSV** | Muy Alta | Grandes volúmenes (> 100 asignaciones) | Media |
| **Auto-Asignación** | Muy Alta | Distribución equitativa inicial | Baja |
| **Exportar/Editar/Importar** | Alta | Duplicar ciclo anterior con cambios | Media |

## Workflow Recomendado para Nuevo Ciclo Escolar

### Opción A: Desde Cero

1. **Preparación** (30 min):
   - Verifica que todos los profesores estén cargados y activos
   - Verifica que todas las materias estén cargadas y activas
   - Descarga plantilla CSV

2. **Asignación** (1-2 horas):
   - Completa el CSV con las asignaciones
   - O usa auto-asignación por carrera y luego ajusta
   - Importa el CSV

3. **Revisión** (30 min):
   - Revisa cargas de trabajo
   - Ajusta distribución si es necesaria
   - Verifica materias críticas asignadas a profesores especializados

4. **Guardado y Prueba** (15 min):
   - Guarda todos los cambios
   - Exporta para tener respaldo
   - Prueba en el módulo de horarios

**Tiempo total**: 2-3 horas para un sistema completo

### Opción B: Duplicar Ciclo Anterior

1. **Exportación** (5 min):
   - Exporta asignaciones del ciclo anterior
   
2. **Edición** (30-60 min):
   - Abre CSV en Excel
   - Actualiza profesores nuevos/retirados
   - Ajusta materias modificadas

3. **Importación** (5 min):
   - Importa CSV actualizado

4. **Revisión y Ajustes** (30 min):
   - Revisa cambios aplicados
   - Ajusta lo necesario manualmente

**Tiempo total**: 1-2 horas

## Soporte y Contacto

Para problemas o sugerencias sobre este módulo:
- Contacta al administrador del sistema
- Revisa los logs de errores en caso de fallas
- Consulta la documentación general del sistema

## Historial de Cambios

### Versión 2.0 (Actual)
- ✨ Importación masiva desde CSV
- ✨ Auto-asignación inteligente por carrera
- ✨ Exportación de asignaciones actuales
- ✨ Indicadores de carga de trabajo
- ✨ Herramientas de selección masiva mejoradas
- ✨ Filtro de profesores con capacidad
- ✨ Contador de cambios en tiempo real
- ✨ Interfaz visual mejorada con código de colores

### Versión 1.0
- Interfaz básica de matriz
- Asignación manual individual
- Filtros por carrera y cuatrimestre
