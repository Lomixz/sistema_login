# Generación Masiva de Horarios - Equilibrio entre Grupos

## 🎯 Problema que Resuelve

### ❌ Problema Anterior (Generación Individual):

Si generamos horarios grupo por grupo:

```
Grupo A (generado primero):
✅ Tiene acceso a TODOS los profesores disponibles
✅ Puede tomar los MEJORES horarios (9am-12pm)
✅ Profesores con disponibilidad completa

Grupo B (generado después):
⚠️  Profesores ya tienen clases con Grupo A
⚠️  Solo quedan horarios menos convenientes
⚠️  Menos opciones de distribución

Grupo C (generado al final):
❌ Profesores muy ocupados con A y B
❌ Solo quedan horarios "feos" (muy temprano o muy tarde)
❌ Horarios fragmentados y dispersos
```

### ✅ Solución: Generación Masiva

Todos los grupos se generan **simultáneamente** en un solo proceso de optimización:

```
Grupos A, B, C (generados juntos):
✅ TODOS compiten equitativamente por los mejores horarios
✅ Profesores se distribuyen balanceadamente entre grupos
✅ Calidad similar de horarios para todos
✅ Optimización global del sistema
```

## 🚀 Cómo Funciona

### 1. Clase `GeneradorHorariosMasivo`

Esta nueva clase extiende el generador individual para manejar múltiples grupos:

```python
from generador_horarios import generar_horarios_masivos

# IDs de todos los grupos que quieres generar
grupos_ids = [1, 2, 3, 4, 5]  # Por ejemplo, todos los grupos de 3er cuatrimestre

resultado = generar_horarios_masivos(
    grupos_ids=grupos_ids,
    periodo_academico='2025-1',
    version_nombre='Final',
    creado_por=usuario.id
)

if resultado['exito']:
    print(f"✅ Horarios generados para {resultado['grupos_procesados']} grupos")
    print(f"📊 Total de horarios: {resultado['horarios_generados']}")
else:
    print(f"❌ Error: {resultado['mensaje']}")
```

### 2. Variables de Decisión

En lugar de: `(profesor, materia, horario, día)`

Ahora son: `(GRUPO, profesor, materia, horario, día)`

Esto permite que el solver considere todas las asignaciones de todos los grupos simultáneamente.

### 3. Restricción Crítica: No Conflicto Global

```python
def restriccion_no_conflicto_profesor_global(self):
    """
    Un profesor NO puede dar clases simultáneas en diferentes grupos
    """
    # Para cada profesor, en cada momento (horario + día):
    # sum(asignaciones_en_todos_los_grupos) <= 1
```

Esta es la restricción más importante en la generación masiva. Asegura que:
- Un profesor no tenga clase con Grupo A y Grupo B al mismo tiempo
- La disponibilidad del profesor se respete globalmente
- No haya conflictos entre grupos

### 4. Función Objetivo Equilibrada

La función objetivo tiene componentes especiales para generación masiva:

#### Componente 1: Equidad de Carga (Peso 5)
```python
# Minimizar diferencia entre el profesor con más y menos horas
# Distribuye el trabajo equitativamente
```

#### Componente 2: Equilibrio de Calidad entre Grupos (Peso 8) ⭐ NUEVO
```python
# Penaliza cuando un grupo tiene horarios "feos" y otro tiene "buenos"
# Busca que todos los grupos tengan calidad similar

Penalizaciones:
- Horarios muy tempranos (primeras 2 horas): penalización 3
- Horarios muy tardíos (últimas 2 horas): penalización 2
- Horarios medios: penalización 0 (preferidos)

# Minimiza la diferencia de penalización entre grupos
# Resultado: Todos los grupos tienen horarios decentes
```

## 📊 Comparación: Individual vs Masivo

### Escenario: 5 grupos de 3er cuatrimestre

#### Generación Individual (uno por uno):

```
┌─────────┬───────────────┬──────────────┬─────────────────┐
│ Grupo   │ Horarios 9-12 │ Profesores   │ Calidad         │
├─────────┼───────────────┼──────────────┼─────────────────┤
│ Grupo A │ 80% clases    │ 100% disp    │ ⭐⭐⭐⭐⭐ (5/5) │
│ Grupo B │ 60% clases    │ 70% disp     │ ⭐⭐⭐⭐ (4/5)   │
│ Grupo C │ 40% clases    │ 50% disp     │ ⭐⭐⭐ (3/5)     │
│ Grupo D │ 20% clases    │ 30% disp     │ ⭐⭐ (2/5)       │
│ Grupo E │ 10% clases    │ 20% disp     │ ⭐ (1/5)         │
└─────────┴───────────────┴──────────────┴─────────────────┘

Promedio: 3/5 ⭐⭐⭐
Desviación: MUY ALTA ❌
Estudiantes del Grupo E: INSATISFECHOS 😞
```

#### Generación Masiva (todos juntos):

```
┌─────────┬───────────────┬──────────────┬─────────────────┐
│ Grupo   │ Horarios 9-12 │ Profesores   │ Calidad         │
├─────────┼───────────────┼──────────────┼─────────────────┤
│ Grupo A │ 50% clases    │ 60% disp     │ ⭐⭐⭐⭐ (4/5)   │
│ Grupo B │ 55% clases    │ 65% disp     │ ⭐⭐⭐⭐ (4/5)   │
│ Grupo C │ 45% clases    │ 55% disp     │ ⭐⭐⭐⭐ (4/5)   │
│ Grupo D │ 50% clases    │ 60% disp     │ ⭐⭐⭐⭐ (4/5)   │
│ Grupo E │ 48% clases    │ 58% disp     │ ⭐⭐⭐⭐ (4/5)   │
└─────────┴───────────────┴──────────────┴─────────────────┘

Promedio: 4/5 ⭐⭐⭐⭐
Desviación: MUY BAJA ✅
TODOS los estudiantes: SATISFECHOS 😊
```

## 💡 Ventajas de la Generación Masiva

### 1. **Equidad entre Grupos** 🎯
- Todos los grupos tienen acceso justo a profesores y horarios
- No hay grupos "privilegiados" ni "desfavorecidos"
- Calidad homogénea para todos los estudiantes

### 2. **Optimización Global** 🌍
- El solver ve TODO el panorama a la vez
- Puede encontrar soluciones que no serían posibles generando uno por uno
- Mejor uso de recursos (profesores y horarios)

### 3. **Consistencia** 📋
- Un solo proceso de generación
- Todos los horarios con la misma versión
- Fácil de auditar y validar

### 4. **Eficiencia** ⚡
- Aunque toma más tiempo, es una sola ejecución
- No hay que ejecutar el generador 5 veces
- Menos riesgo de conflictos

### 5. **Satisfacción Estudiantil** 😊
- Estudiantes de todos los grupos tienen buenos horarios
- Reduce quejas y solicitudes de cambios
- Mejor percepción del sistema

## 🔧 Uso Práctico

### Caso de Uso 1: Generar Todos los Grupos de un Cuatrimestre

```python
from models import Grupo
from generador_horarios import generar_horarios_masivos

# Obtener todos los grupos de 3er cuatrimestre, turno matutino
grupos = Grupo.query.filter_by(
    cuatrimestre=3,
    turno='M',
    activo=True
).all()

grupos_ids = [g.id for g in grupos]

resultado = generar_horarios_masivos(
    grupos_ids=grupos_ids,
    periodo_academico='2025-1',
    version_nombre='Final Cuatri 3',
    creado_por=current_user.id
)
```

### Caso de Uso 2: Generar Toda una Carrera

```python
# Obtener todos los grupos de Ingeniería en Software
carrera = Carrera.query.filter_by(nombre='Ingeniería en Software').first()
grupos = Grupo.query.filter_by(carrera_id=carrera.id, activo=True).all()

grupos_ids = [g.id for g in grupos]

resultado = generar_horarios_masivos(
    grupos_ids=grupos_ids,
    periodo_academico='2025-1',
    version_nombre='Final ISW Completa',
    creado_por=current_user.id
)
```

### Caso de Uso 3: Generar por Turno

```python
# Todos los grupos matutinos de toda la institución
grupos_matutinos = Grupo.query.filter_by(turno='M', activo=True).all()
grupos_ids = [g.id for g in grupos_matutinos]

resultado = generar_horarios_masivos(
    grupos_ids=grupos_ids,
    periodo_academico='2025-1',
    version_nombre='Final Turno Matutino',
    creado_por=current_user.id
)
```

## ⚙️ Consideraciones Técnicas

### Tiempo de Ejecución

```
Grupos Individuales:
1 grupo:  1-2 minutos
5 grupos: 5-10 minutos (suma)

Generación Masiva:
5 grupos: 5-10 minutos (TOTAL)
```

- **Tiempo similar o menor** que generar individualmente
- Configurado para máximo 10 minutos (600 segundos)
- Usa 8 hilos en paralelo

### Requisitos

- ✅ **OR-Tools obligatorio** (no hay fallback para generación masiva)
- ✅ Todos los grupos deben tener materias asignadas
- ✅ Todas las materias deben tener profesores asignados
- ✅ Profesores deben tener disponibilidad configurada

### Memoria y Recursos

```
Variables de decisión:
Individual: ~1,000 - 5,000 variables por grupo
Masivo (5 grupos): ~5,000 - 25,000 variables

Restricciones:
Individual: ~500 - 2,000 restricciones por grupo
Masivo (5 grupos): ~2,500 - 10,000 restricciones
```

El solver de Google OR-Tools está optimizado para manejar estos volúmenes sin problemas.

## 📝 Validaciones

Antes de generar, el sistema valida:

```python
✅ Todos los grupos existen en la base de datos
✅ Todos los grupos tienen materias asignadas
✅ Todas las materias tienen profesores asignados
✅ Profesores tienen disponibilidad configurada
✅ Hay suficientes horarios disponibles

Si algo falla, muestra mensaje claro:
❌ Grupo ISW-3A: sin materias asignadas
❌ Grupo ISW-3B: materias sin profesor (Cálculo, Física)
```

## 🎓 Recomendaciones

### ✅ Cuándo Usar Generación Masiva:

1. **Al inicio del semestre**: Generar todos los horarios de una vez
2. **Por cuatrimestre**: Generar todos los grupos del mismo cuatrimestre juntos
3. **Por carrera**: Generar toda una carrera completa
4. **Por turno**: Matutino y vespertino por separado

### ⚠️ Cuándo NO Usar Generación Masiva:

1. **Un solo grupo nuevo**: Si solo agregaste un grupo, genera solo ese
2. **Corrección puntual**: Si solo quieres ajustar un grupo específico
3. **Pruebas**: Para probar configuraciones, usa individual primero

### 💡 Mejor Práctica:

```
1. Configurar TODOS los grupos (materias + profesores)
2. Configurar disponibilidades de profesores
3. Generar TODO de una vez con generación masiva
4. Revisar resultados
5. Ajustes puntuales si es necesario (regenerar masivo o individual)
```

## 🔮 Resultado Esperado

Después de la generación masiva:

```
✅ Todos los grupos tienen horarios completos
✅ Profesores distribuidos equitativamente
✅ Calidad similar en todos los horarios
✅ Horas agrupadas (min. horas muertas)
✅ Respeta todas las disponibilidades
✅ Cumple todas las restricciones
```

## 📞 Soporte

Si la generación masiva falla:

1. **Verifica que OR-Tools esté instalado**: `pip install ortools`
2. **Valida los grupos**: Todos con materias y profesores
3. **Revisa disponibilidades**: Profesores deben tener horas marcadas
4. **Verifica memoria**: Para muchos grupos (>20), puede requerir más RAM
5. **Lee los mensajes de error**: El sistema da mensajes claros de qué falta

## 🎉 Conclusión

La generación masiva es la **mejor forma** de crear horarios cuando tienes múltiples grupos:

- ✅ Equidad total entre grupos
- ✅ Mejor optimización global
- ✅ Menos quejas de estudiantes
- ✅ Ahorro de tiempo administrativo
- ✅ Horarios de calidad homogénea

**¡Adiós a los grupos con horarios "feos"! 🎊**
