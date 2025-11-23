# Optimización de Horas de Trabajo para Profesores

## 📋 Descripción

Este documento describe las mejoras implementadas en el generador de horarios para optimizar la distribución de horas de los profesores, especialmente aquellos que vienen de lejos y necesitan evitar muchas horas muertas entre clases.

## 🎯 Objetivos

1. **Agrupar horas de trabajo** en bloques continuos
2. **Limitar horas muertas** a máximo 2 horas libres entre clases
3. **Concentrar días de trabajo** para reducir desplazamientos
4. **Mantener todas las restricciones** existentes de disponibilidad y carga horaria

## 🔧 Restricciones Implementadas

### 1. Restricción de Horas Muertas (Máximo 2 horas libres)

**Método:** `restriccion_horas_muertas_profesor()`

**Funcionamiento:**
- Si un profesor tiene clase en el horario `i` y luego tiene clase en el horario `j`, donde `j - i > 3` (más de 2 horas de diferencia)
- Entonces **debe** tener al menos una clase en alguno de los horarios intermedios
- Esto evita que un profesor tenga, por ejemplo, clase a las 7am y luego no tenga nada hasta las 12pm

**Ejemplo:**
```
❌ Antes (5 horas muertas):
07:00-08:00 → Clase de Matemáticas
08:00-09:00 → Libre
09:00-10:00 → Libre
10:00-11:00 → Libre
11:00-12:00 → Libre
12:00-13:00 → Clase de Física

✅ Después (máximo 2 horas muertas):
07:00-08:00 → Clase de Matemáticas
08:00-09:00 → Libre
09:00-10:00 → Libre
10:00-11:00 → Clase de Álgebra (rellena el hueco)
11:00-12:00 → Libre
12:00-13:00 → Clase de Física
```

### 2. Restricción de Bloques Continuos

**Método:** `restriccion_bloques_continuos_profesor()`

**Funcionamiento:**
- Fomenta que las clases de un profesor estén agrupadas en bloques consecutivos
- Reduce las "islas" de horas libres entre clases
- Trabaja en conjunto con la función objetivo para penalizar horarios dispersos

### 3. Función Objetivo Mejorada

**Método:** `agregar_funcion_objetivo()`

La función objetivo ahora tiene **múltiples componentes ponderados**:

#### Componente 1: Equidad de Carga (Peso 5)
- Minimiza la diferencia entre el profesor con más horas y el que tiene menos
- Distribuye equitativamente la carga de trabajo

#### Componente 2: Minimizar Transiciones (Peso 10) ⭐ MÁS IMPORTANTE
- Cuenta el número de veces que un profesor pasa de "tener clase" a "no tener clase" o viceversa
- **Minimizar transiciones = Maximizar bloques continuos**
- Este es el componente con mayor peso (10) porque es el más importante para profesores de lejos

**Ejemplo:**
```
❌ Muchas transiciones (6 cambios):
Libre → CLASE (transición 1)
CLASE → Libre (transición 2)
Libre → CLASE (transición 3)
CLASE → Libre (transición 4)
Libre → CLASE (transición 5)
CLASE → Libre (transición 6)

✅ Pocas transiciones (2 cambios):
Libre → Libre
Libre → CLASE (transición 1)
CLASE → CLASE
CLASE → CLASE
CLASE → Libre (transición 2)
Libre → Libre
```

#### Componente 3: Concentrar Días (Peso 3)
- Minimiza el número total de días en los que un profesor tiene clases
- Prefiere que un profesor trabaje 3 días completos en lugar de 5 días con pocas horas

**Ejemplo:**
```
❌ Antes (5 días dispersos):
Lunes:     2 horas
Martes:    2 horas
Miércoles: 2 horas
Jueves:    2 horas
Viernes:   2 horas
Total: 10 horas en 5 días

✅ Después (3 días concentrados):
Lunes:     4 horas (bloque continuo)
Martes:    Libre (no viene)
Miércoles: 3 horas (bloque continuo)
Jueves:    Libre (no viene)
Viernes:   3 horas (bloque continuo)
Total: 10 horas en 3 días
```

## 📊 Impacto Esperado

### Para Profesores de Lejos:
- ✅ **Menos viajes**: Concentración de horas en menos días
- ✅ **Menos tiempo perdido**: Máximo 2 horas libres entre clases
- ✅ **Bloques continuos**: Trabajo agrupado, menos fragmentación
- ✅ **Mejor aprovechamiento**: Si vienen, tienen suficiente carga ese día

### Para el Sistema:
- ✅ **Optimización automática**: El solver busca la mejor distribución
- ✅ **Balance múltiple**: Considera equidad, continuidad y concentración
- ✅ **Respeta disponibilidad**: Mantiene todas las restricciones de disponibilidad
- ✅ **Mejor experiencia**: Profesores más satisfechos = mejor enseñanza

## 🔍 Cómo Verlo en Acción

Cuando se genera un horario, el sistema mostrará:

```
🚀 Iniciando generación de horarios con Google OR-Tools CP-SAT...
======================================================================
📋 RESTRICCIONES APLICADAS:
   1. ✓ Cada materia debe tener sus horas semanales requeridas
   2. ✓ Un profesor NO puede tener dos clases simultáneas
   3. ✓ Profesores SOLO dan clases en horas marcadas como disponibles
   4. ✓ Máximo 3 HORAS SEGUIDAS de la misma materia por día
   5. ✓ Máximo 8 HORAS de trabajo por día por profesor
   6. ✓ Carga máxima semanal: 40h (tiempo completo) / 20h (asignatura)
   7. ✓ Sin conflictos de horario entre carreras
   8. ✓ MÁXIMO 2 HORAS LIBRES entre clases (profesores de lejos)
   9. ✓ BLOQUES CONTINUOS de trabajo (minimizar horas muertas)

🎯 OPTIMIZACIÓN:
   • Agrupar horas de trabajo en bloques continuos
   • Minimizar transiciones y horas muertas
   • Concentrar días de trabajo
   • Distribuir carga equitativamente entre profesores
```

## 💡 Ejemplo Real

### Antes de la Optimización:
```
Profesor Juan Pérez (viene de 2 horas de distancia):

Lunes:
07:00-08:00 → Matemáticas I
08:00-09:00 → LIBRE
09:00-10:00 → LIBRE
10:00-11:00 → LIBRE
11:00-12:00 → Álgebra
(4 horas muertas esperando)

Martes:
07:00-08:00 → LIBRE
08:00-09:00 → Cálculo
09:00-10:00 → LIBRE
10:00-11:00 → LIBRE
(Viaje para solo 1 hora de clase)
```

### Después de la Optimización:
```
Profesor Juan Pérez (viene de 2 horas de distancia):

Lunes:
07:00-08:00 → Matemáticas I
08:00-09:00 → Álgebra
09:00-10:00 → Cálculo
10:00-11:00 → LIBRE (solo 1 hora libre)
11:00-12:00 → Geometría
(Bloque continuo de trabajo: 4 clases con solo 1 hora libre)

Martes:
(Día libre - no viene)
```

## 🚀 Ventajas del Nuevo Sistema

1. **Basado en OR-Tools**: Usa algoritmos de optimización de Google
2. **Múltiples objetivos**: Balancea varios criterios simultáneamente
3. **Pesos configurables**: Los pesos (5, 10, 3) pueden ajustarse según necesidades
4. **Respeta restricciones**: Nunca viola disponibilidad ni límites de horas
5. **Solución óptima**: Encuentra la mejor distribución posible automáticamente

## 📝 Notas Técnicas

### Variables de Decisión
- Una variable booleana por cada combinación de: `(profesor, materia, horario, día)`
- El solver decide cuáles variables son `1` (asignadas) y cuáles son `0` (no asignadas)

### Restricciones Hard vs Soft
- **Hard (obligatorias)**: Disponibilidad, no conflictos, horas por materia
- **Soft (optimizables)**: Minimizar transiciones, concentrar días

### Tiempo de Resolución
- Máximo 5 minutos (300 segundos)
- Usa 8 hilos en paralelo para acelerar la búsqueda
- Encuentra soluciones factibles rápidamente, luego las mejora

## 🔮 Mejoras Futuras Posibles

1. **Preferencias por profesor**: Algunos profesores pueden preferir días dispersos
2. **Horarios preferidos**: Profesores que prefieren mañanas o tardes
3. **Desplazamiento real**: Integrar distancias reales desde Google Maps
4. **Reportes de optimización**: Mostrar métricas de cuántas horas se ahorraron

## 📚 Referencias

- [Google OR-Tools CP-SAT Solver](https://developers.google.com/optimization/cp/cp_solver)
- Documentación interna: `generador_horarios.py`
- Modelo de datos: `models.py` (DisponibilidadProfesor, HorarioAcademico)
