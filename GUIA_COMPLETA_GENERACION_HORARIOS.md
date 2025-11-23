# Sistema de Generación de Horarios - Guía Completa

## 📚 Índice

1. [Resumen del Sistema](#resumen-del-sistema)
2. [Generación Individual vs Masiva](#generación-individual-vs-masiva)
3. [Características Principales](#características-principales)
4. [Guía de Uso](#guía-de-uso)
5. [Optimizaciones Implementadas](#optimizaciones-implementadas)
6. [Restricciones del Sistema](#restricciones-del-sistema)
7. [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Resumen del Sistema

El sistema utiliza **Google OR-Tools CP-SAT Solver**, un motor de optimización avanzado, para generar horarios académicos automáticamente. El sistema considera múltiples restricciones y optimiza la distribución de profesores, horarios y materias.

### Tecnologías Utilizadas

- **Google OR-Tools**: Motor de optimización
- **Python**: Lenguaje de programación
- **Flask**: Framework web
- **SQLAlchemy**: ORM para base de datos

---

## 🔄 Generación Individual vs Masiva

### Generación Individual

**Cuando usarla:**
- Un solo grupo nuevo
- Ajustes puntuales
- Pruebas de configuración

**Características:**
- ✅ Rápida (1-3 minutos)
- ✅ Fácil de usar
- ⚠️ Los primeros grupos tienen mejores horarios

**Ejemplo de uso:**
```
Grupo ISW-3A recién creado
→ Generar solo para ISW-3A
```

### Generación Masiva ⭐ RECOMENDADA

**Cuando usarla:**
- Inicio de semestre
- Múltiples grupos del mismo cuatrimestre
- Toda una carrera
- Cuando se quiere equidad total

**Características:**
- ✅ Todos los grupos equilibrados
- ✅ Sin grupos privilegiados
- ✅ Optimización global
- ⚠️ Toma más tiempo (5-10 minutos)

**Ejemplo de uso:**
```
Todos los grupos de 3er cuatrimestre
→ Generar masivamente
→ Todos tienen horarios de calidad similar
```

### Comparación Visual

```
┌─────────────────────┬──────────────────┬──────────────────┐
│ Característica      │ Individual       │ Masiva           │
├─────────────────────┼──────────────────┼──────────────────┤
│ Grupos por vez      │ 1                │ Múltiples        │
│ Tiempo (5 grupos)   │ 5-10 min (total) │ 5-10 min (total) │
│ Equidad             │ ⭐⭐             │ ⭐⭐⭐⭐⭐       │
│ Optimización        │ Local            │ Global           │
│ Recomendado para    │ Casos puntuales  │ Generación masiva│
└─────────────────────┴──────────────────┴──────────────────┘
```

---

## ✨ Características Principales

### 1. Respeto de Disponibilidad de Profesores

```
Profesor Juan:
Lunes 7-9am: ✅ Disponible
Lunes 9-10am: ❌ No disponible
→ Sistema NUNCA le asignará clase de 9-10am
```

### 2. Agrupación de Horas (Profesores de Lejos)

```
❌ Antes:
07:00 - Clase
08:00 - LIBRE
09:00 - LIBRE  
10:00 - LIBRE
11:00 - Clase
(4 horas muertas)

✅ Después:
07:00 - Clase
08:00 - Clase
09:00 - LIBRE (máx 2 horas)
10:00 - Clase
(Solo 1 hora muerta)
```

### 3. Bloques Continuos de Trabajo

```
✅ Preferido:
Lunes:   8-12pm (4 horas continuas)
Martes:  LIBRE
Miércoles: 8-12pm (4 horas continuas)

❌ Evitado:
Lunes:   8-9, 11-12 (fragmentado)
Martes:  9-10, 2-3 (fragmentado)
Miércoles: 8-9, 12-1 (fragmentado)
```

### 4. Concentración de Días

```
✅ Mejor:
10 horas en 3 días (menos viajes)

❌ Peor:
10 horas en 5 días (más viajes)
```

### 5. Distribución Equitativa

```
Profesor A: 15 horas
Profesor B: 16 horas  ✅ Equilibrado
Profesor C: 15 horas

vs

Profesor A: 25 horas
Profesor B: 10 horas  ❌ Desequilibrado
Profesor C: 5 horas
```

---

## 📖 Guía de Uso

### Paso 1: Preparación

1. **Configurar Grupos**
   - Crear grupos en el sistema
   - Asignar carrera y cuatrimestre
   - Definir turno (Matutino/Vespertino)

2. **Asignar Materias a Grupos**
   - Ir a "Asignar Materias a Grupo"
   - Seleccionar las materias del cuatrimestre

3. **Asignar Profesores a Materias**
   - Ir a "Asignar Profesores"
   - Cada materia debe tener al menos un profesor

4. **Configurar Disponibilidad**
   - Cada profesor debe marcar sus horas disponibles
   - Ir a "Disponibilidad de Profesores"

### Paso 2: Generar Horarios

#### Opción A: Generación Individual

1. Ir a: **Admin → Horarios Académicos → Generar Individual**
2. Seleccionar el grupo
3. Configurar:
   - Días de la semana (Lun-Vie o Lun-Sáb)
   - Nombre de versión (opcional)
4. Clic en "Generar Horarios"
5. Esperar 1-3 minutos
6. ✅ Revisar resultados

#### Opción B: Generación Masiva ⭐

1. Ir a: **Admin → Horarios Académicos → Generar Masivo**
2. Seleccionar grupos:
   - Por carrera completa
   - Por cuatrimestre específico
   - Grupos individuales
3. Configurar:
   - Nombre de versión (Ej: "Final Cuatri 3")
   - Días de la semana
4. Clic en "Generar Horarios Masivos"
5. Esperar 5-10 minutos (según cantidad)
6. ✅ Revisar resultados

### Paso 3: Verificación

1. **Ver Horarios Generados**
   - Ir a "Gestión de Horarios Académicos"
   - Filtrar por grupo o profesor

2. **Validar Calidad**
   - ✅ Todas las materias tienen sus horas
   - ✅ No hay conflictos de horario
   - ✅ Profesores en horas disponibles
   - ✅ Bloques de trabajo agrupados

3. **Ajustes si es Necesario**
   - Editar horarios individuales
   - O regenerar si hay problemas mayores

---

## 🎯 Optimizaciones Implementadas

### 1. Horas Muertas Limitadas

**Archivo:** `generador_horarios.py` → `restriccion_horas_muertas_profesor()`

```python
Restricción:
Si profesor tiene clase en hora I y hora J (con más de 2 horas entre ellas)
→ Debe tener al menos una clase intermedia
```

**Impacto:** Profesores no tienen más de 2 horas libres entre clases

### 2. Bloques Continuos

**Archivo:** `generador_horarios.py` → `restriccion_bloques_continuos_profesor()`

**Impacto:** Clases se agrupan en bloques, reduciendo fragmentación

### 3. Función Objetivo Multi-componente

**Archivo:** `generador_horarios.py` → `agregar_funcion_objetivo()`

**Componentes:**
1. Equidad de carga (peso 5)
2. Minimizar transiciones (peso 10) ⭐
3. Concentrar días (peso 3)

**En generación masiva:**
4. Equilibrio entre grupos (peso 8) ⭐

### 4. Equilibrio Global (Solo Masiva)

**Archivo:** `generador_horarios.py` → `GeneradorHorariosMasivo`

```python
Penalizaciones por horario:
- Muy temprano (primeras 2 horas): +3 puntos
- Muy tarde (últimas 2 horas): +2 puntos
- Horarios medios: +0 puntos

→ Minimizar diferencia de penalizaciones entre grupos
→ Todos los grupos tienen calidad similar
```

---

## 🔒 Restricciones del Sistema

### Restricciones Obligatorias (Hard Constraints)

1. **Horas por Materia**
   - Cada materia debe tener exactamente sus horas semanales configuradas

2. **No Conflictos de Profesor**
   - Un profesor NO puede tener dos clases simultáneas

3. **No Conflictos de Grupo**
   - Un grupo NO puede tener dos materias al mismo tiempo

4. **Disponibilidad**
   - Profesores SOLO en horas marcadas como disponibles

5. **Carga Máxima**
   - Tiempo completo: máx 40 horas/semana
   - Asignatura: máx 20 horas/semana

6. **Máximo Diario**
   - Ningún profesor más de 8 horas/día

7. **Distribución de Materia**
   - Máximo 3 horas seguidas de la misma materia/día

### Restricciones Óptimas (Soft Constraints)

8. **Horas Muertas**
   - Máximo 2 horas libres entre clases (se intenta cumplir)

9. **Bloques Continuos**
   - Preferir clases agrupadas vs dispersas

10. **Equidad de Carga**
    - Distribuir trabajo equitativamente

11. **Equilibrio entre Grupos** (solo masiva)
    - Todos los grupos con calidad similar

---

## 🔧 Solución de Problemas

### Problema: "No se encontró solución factible"

**Causas comunes:**

1. **Falta de disponibilidad**
   ```
   Solución: Asegurar que profesores tengan suficientes horas disponibles
   Revisar: Admin → Disponibilidad de Profesores
   ```

2. **Demasiadas horas requeridas, pocos horarios**
   ```
   Ejemplo:
   - Materias requieren: 45 horas/semana
   - Horarios disponibles: 8 horarios × 5 días = 40 bloques
   
   Solución:
   - Agregar día sábado, O
   - Agregar más horarios al turno, O
   - Reducir horas de algunas materias
   ```

3. **Profesores sin disponibilidad configurada**
   ```
   Solución: Cada profesor debe marcar al menos algunas horas disponibles
   ```

### Problema: "Horarios muy dispersos"

```
Causa: El solver encontró una solución válida pero no óptima

Solución:
1. Aumentar tiempo de resolución (en código)
2. Ajustar pesos de la función objetivo
3. Usar generación masiva (mejor optimización global)
```

### Problema: "Grupo sin profesor asignado a materia"

```
Error: "Materias sin profesor asignado: Cálculo, Física"

Solución:
1. Ir a: Asignar Profesores
2. Asignar al menos un profesor activo a cada materia
3. Intentar generar nuevamente
```

### Problema: "Generación masiva muy lenta"

```
Normal: 5-10 minutos para 5-10 grupos

Si toma más de 15 minutos:
1. Verificar que OR-Tools esté instalado correctamente
2. Reducir número de grupos (dividir en lotes)
3. Verificar recursos del servidor (RAM, CPU)
```

---

## 📊 Mejores Prácticas

### ✅ Recomendaciones

1. **Usa Generación Masiva al inicio del semestre**
   - Genera todos los grupos de un cuatrimestre juntos
   - Mejor equidad y optimización

2. **Configura disponibilidades realistas**
   - Profesores deben marcar sus horas reales
   - Más horas disponibles = mejor optimización

3. **Agrupa por cuatrimestre o carrera**
   - No mezcles cuatrimestres muy diferentes
   - Mejor generar por turno (matutino separado de vespertino)

4. **Revisa antes de publicar**
   - Usa "versiones" con nombres descriptivos
   - Revisa calidad antes de hacer final

5. **Mantén configuraciones actualizadas**
   - Horas de materias correctas
   - Disponibilidades de profesores al día

### ⚠️ Evitar

1. ❌ Generar individualmente muchos grupos uno por uno
2. ❌ Profesores con poca disponibilidad
3. ❌ Materias sin horas configuradas
4. ❌ Ignorar validaciones del sistema

---

## 📁 Archivos de Documentación

- `OPTIMIZACION_HORAS_PROFESORES.md` - Detalles de optimización de horas
- `GENERACION_MASIVA_HORARIOS.md` - Guía específica de generación masiva
- `generador_horarios.py` - Código fuente del generador
- `app.py` - Rutas web para la generación

---

## 🎓 Conclusión

El sistema de generación de horarios está diseñado para:

✅ Respetar disponibilidades
✅ Optimizar distribución de profesores
✅ Minimizar horas muertas
✅ Agrupar trabajo en bloques continuos
✅ Equilibrar carga entre profesores
✅ En modo masivo: equilibrar calidad entre grupos

**Resultado:** Horarios de alta calidad que benefician tanto a profesores como a estudiantes.

---

## 📞 Soporte

Si tienes problemas:

1. Lee los mensajes de error (son descriptivos)
2. Revisa esta guía
3. Verifica configuraciones (grupos, materias, profesores, disponibilidades)
4. Consulta los logs del sistema

**¡Buena suerte generando horarios! 🚀**
