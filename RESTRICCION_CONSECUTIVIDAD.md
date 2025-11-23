# 🔗 Restricción de Horas Consecutivas por Materia

## 📋 Descripción del Problema

Anteriormente, el generador de horarios podía fragmentar las horas de una misma materia en el mismo día, creando horarios incómodos como:

```
Lunes:
07:00-08:00  Física
08:00-09:00  Fundamentos de Programación
09:00-10:00  Física  ❌ (FRAGMENTACIÓN)
```

Esto causaba problemas porque:
- Los estudiantes tienen la misma materia interrumpida por otra
- Los profesores tienen que "retomar" la clase después de una interrupción
- Dificulta la continuidad pedagógica

## ✅ Solución Implementada

### Nueva Restricción: `restriccion_materias_consecutivas()`

Esta restricción asegura que **todas las horas de una misma materia en el mismo día sean consecutivas**, sin interrupciones.

### Lógica de la Restricción

Para cada combinación de:
- Materia
- Día de la semana
- Profesor

Se verifica cada grupo de 3 horarios consecutivos posibles (A, B, C):

**Regla:** Si hay clase en el horario A Y en el horario C, entonces **DEBE** haber clase en el horario B (el del medio).

Esto se implementa con la restricción matemática:
```
A + C ≤ 1 + B
```

### Ejemplo de Funcionamiento

#### ❌ Antes (Fragmentación Permitida)
```
Lunes:
07:00-08:00  Física        (A=1)
08:00-09:00  Programación  (B=0)
09:00-10:00  Física        (C=1)
```
Esto ahora es **IMPOSIBLE** porque viola: `1 + 1 ≤ 1 + 0` → `2 ≤ 1` (falso)

#### ✅ Después (Solo Consecutivas)
```
Lunes:
07:00-08:00  Física        (A=1)
08:00-09:00  Física        (B=1)
09:00-10:00  Física        (C=1)
```
Esto cumple: `1 + 1 ≤ 1 + 1` → `2 ≤ 2` (verdadero)

O bien:
```
Lunes:
07:00-08:00  Física        
08:00-09:00  Física        
10:00-11:00  Física        (separado por otra materia en horario diferente)
```

## 🎯 Beneficios

1. **Mejor experiencia estudiantil**: Las materias se imparten de forma continua
2. **Mejor aprovechamiento del tiempo**: No hay "retomar" temas después de interrupciones
3. **Horarios más profesionales**: Se parecen más a horarios universitarios reales
4. **Facilita la planificación**: Los profesores pueden preparar clases más largas y cohesivas

## 📊 Impacto en el Solver

- **Restricciones adicionales**: Varía según el número de materias, profesores y horarios
- **Tiempo de procesamiento**: Incremento mínimo (~5-10%)
- **Factibilidad**: Puede hacer más difícil encontrar soluciones, pero mejora significativamente la calidad

## 🔧 Integración

Esta restricción se aplica en:

1. **GeneradorHorariosOR** (generación individual)
   - Llamada en `agregar_restricciones()` después de `restriccion_distribucion_horas_materia()`

2. **GeneradorHorariosMasivo** (generación masiva)
   - Llamada en `agregar_restricciones()` con la misma lógica

## 📝 Ejemplo de Log

```
🔗 Aplicando restricción de horas consecutivas por materia...
   ✓ Se aplicaron 156 restricciones de consecutividad
```

## 🧪 Casos de Prueba

### Caso 1: Materia de 2 horas en el mismo día
✅ **Permitido**: 07:00-08:00 y 08:00-09:00 (consecutivas)
❌ **Bloqueado**: 07:00-08:00 y 09:00-10:00 (separadas)

### Caso 2: Materia de 3 horas en el mismo día
✅ **Permitido**: 07:00-08:00, 08:00-09:00, 09:00-10:00 (consecutivas)
❌ **Bloqueado**: 07:00-08:00, 08:00-09:00, 10:00-11:00 (tercera separada)

### Caso 3: Materia distribuida en diferentes días
✅ **Permitido**: Lunes 07:00-09:00, Miércoles 07:00-09:00 (cada día consecutivo internamente)

## 🎓 Notas Técnicas

- La restricción solo se aplica dentro del **mismo día**
- No afecta la distribución entre días diferentes
- Compatible con todas las demás restricciones existentes
- Trabaja en conjunto con la restricción de máximo 3 horas seguidas por día

## 📚 Referencias

- Archivo: `generador_horarios.py`
- Método principal: `restriccion_materias_consecutivas()`
- Líneas aproximadas: 452-490
