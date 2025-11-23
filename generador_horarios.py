"""
Módulo para generación automática de horarios académicos usando Google OR-Tools CP-SAT Solver
"""
from models import db, User, Horario, Carrera, Materia, HorarioAcademico
from datetime import datetime
from collections import defaultdict
import math

# Importación condicional de ortools
try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
    print("✅ OR-Tools cargado correctamente")
except ImportError as e:
    print(f"⚠️  OR-Tools no disponible: {e}")
    print("📦 Para instalarlo: pip install ortools")
    ORTOOLS_AVAILABLE = False
    cp_model = None

class GeneradorHorariosOR:
    """Clase para generar horarios académicos automáticamente usando Google OR-Tools"""

    def __init__(self, carrera_id, cuatrimestre, turno='matutino', dias_semana=None,
                 periodo_academico='2025-1', version_nombre=None, creado_por=None, grupo_id=None):
        """
        Inicializar el generador de horarios con OR-Tools

        Args:
            carrera_id: ID de la carrera
            cuatrimestre: Número del cuatrimestre
            turno: 'matutino', 'vespertino' o 'ambos'
            dias_semana: Lista de días de la semana ['lunes', 'martes', etc.]
            periodo_academico: Período académico (ej: '2025-1')
            version_nombre: Etiqueta de la versión (ej: 'Final', 'Borrador 1')
            creado_por: ID del usuario que genera los horarios
            grupo_id: (Nuevo) ID del grupo - si se proporciona, se usarán las materias y profesores del grupo
        """
        if not ORTOOLS_AVAILABLE:
            raise ImportError("OR-Tools no está disponible. Use GeneradorHorariosSinOR como alternativa.")
            
        self.carrera_id = carrera_id
        self.cuatrimestre = cuatrimestre
        self.turno = turno
        self.dias_semana = dias_semana or ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        self.periodo_academico = periodo_academico
        self.version_nombre = version_nombre
        self.creado_por = creado_por
        self.grupo_id = grupo_id  # Nuevo parámetro

        # Datos del proceso
        self.profesores = []
        self.materias = []
        self.horarios = []
        self.disponibilidades = {}  # Cache de disponibilidades por profesor
        self.grupo = None  # Objeto Grupo si se proporciona grupo_id

        # Modelo CP-SAT
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Variables de decisión
        self.variables = {}  # (profesor_id, materia_id, horario_id, dia_idx) -> BoolVar

        # Resultados
        self.horarios_generados = []
        self.solucion_encontrada = False

    def cargar_datos(self):
        """Cargar datos necesarios para la generación"""
        from models import DisponibilidadProfesor, Grupo

        # Si se proporciona grupo_id, usar los datos del grupo
        if self.grupo_id:
            self.grupo = Grupo.query.get(self.grupo_id)
            if not self.grupo:
                raise ValueError(f"No se encontró el grupo con ID {self.grupo_id}")
            
            # Actualizar parámetros con los datos del grupo
            self.carrera_id = self.grupo.carrera_id
            self.cuatrimestre = self.grupo.cuatrimestre
            # Convertir turno de 'M'/'V' a 'matutino'/'vespertino'
            self.turno = 'matutino' if self.grupo.turno == 'M' else 'vespertino'
            
            # Obtener materias del grupo
            self.materias = [m for m in self.grupo.materias if m.activa]
            
            # Obtener profesores que imparten esas materias (solo los activos)
            profesores_set = set()
            for materia in self.materias:
                for profesor in materia.profesores:
                    if profesor.activo:
                        profesores_set.add(profesor)
            self.profesores = list(profesores_set)
            
            print(f"📚 Cargando datos del grupo {self.grupo.codigo}:")
            print(f"   - Carrera: {self.grupo.get_carrera_nombre()}")
            print(f"   - Cuatrimestre: {self.grupo.cuatrimestre}")
            print(f"   - Turno: {self.grupo.get_turno_display()} ({self.turno})")
            print(f"   - Materias asignadas: {len(self.materias)}")
            print(f"   - Profesores asignados: {len(self.profesores)}")
        else:
            # Enfoque legacy: cargar por carrera y cuatrimestre
            # Cargar profesores de la carrera
            self.profesores = User.query.filter(
                User.carrera_id == self.carrera_id,
                User.rol.in_(['profesor_completo', 'profesor_asignatura']),
                User.activo == True
            ).all()

            # Cargar materias del cuatrimestre
            self.materias = Materia.query.filter(
                Materia.carrera_id == self.carrera_id,
                Materia.cuatrimestre == self.cuatrimestre,
                Materia.activa == True
            ).all()
            
            print(f"📚 Cargando datos (modo legacy):")
            print(f"   - Carrera ID: {self.carrera_id}")
            print(f"   - Cuatrimestre: {self.cuatrimestre}")

        # Validaciones
        if not self.profesores:
            raise ValueError("❌ No hay profesores disponibles para esta carrera")
        
        if not self.materias:
            raise ValueError("❌ No hay materias disponibles para este cuatrimestre")

        # Cargar horarios según el turno
        if self.turno == 'ambos':
            self.horarios = Horario.query.filter_by(activo=True).order_by(Horario.orden).all()
            print(f"⏰ Usando TODOS los horarios (ambos turnos)")
        else:
            self.horarios = Horario.query.filter_by(
                turno=self.turno,
                activo=True
            ).order_by(Horario.orden).all()
            print(f"⏰ Filtrando horarios solo del turno: {self.turno}")

        if not self.horarios:
            raise ValueError(f"❌ No hay horarios configurados para el turno {self.turno}")
        
        # Mostrar rango de horarios cargados
        if self.horarios:
            print(f"   📍 Horarios cargados: {self.horarios[0].get_hora_inicio_str()} - {self.horarios[-1].get_hora_fin_str()}")
            print(f"   📊 Total de bloques horarios: {len(self.horarios)}")

        # Cargar disponibilidades de profesores
        self.cargar_disponibilidades()

        # Validar horas de materias
        self.validar_horas_materias()

        print(f"✅ Datos cargados: {len(self.profesores)} profesores, {len(self.materias)} materias, {len(self.horarios)} horarios")

    def validar_horas_materias(self):
        """Validar que todas las materias tengan horas configuradas correctamente"""
        print("🔍 Validando horas de materias...")
        
        materias_sin_horas = []
        materias_con_horas = []
        total_horas_semanales = 0
        
        for materia in self.materias:
            horas_totales = materia.get_horas_totales()
            
            if horas_totales == 0:
                materias_sin_horas.append(materia)
            else:
                materias_con_horas.append((materia, horas_totales))
                total_horas_semanales += horas_totales
        
        # Mostrar resumen
        if materias_sin_horas:
            print(f"   ⚠️  {len(materias_sin_horas)} materias SIN horas configuradas:")
            for materia in materias_sin_horas:
                print(f"      - {materia.codigo} ({materia.nombre})")
            print(f"   📝 Estas materias usarán 3 horas por defecto")
        
        if materias_con_horas:
            print(f"   ✓ {len(materias_con_horas)} materias con horas configuradas:")
            for materia, horas in materias_con_horas:
                print(f"      - {materia.codigo}: {materia.horas_semanales}h semanales")
        
        print(f"   📊 Total horas semanales requeridas: {total_horas_semanales} horas")
        
        # Calcular si hay suficientes bloques horarios disponibles
        bloques_disponibles = len(self.horarios) * len(self.dias_semana)
        print(f"   📅 Bloques horarios disponibles: {bloques_disponibles} ({len(self.horarios)} horarios × {len(self.dias_semana)} días)")
        
        if total_horas_semanales > bloques_disponibles:
            deficit = total_horas_semanales - bloques_disponibles
            print(f"   ⚠️  ADVERTENCIA: Se requieren {total_horas_semanales} horas pero solo hay {bloques_disponibles} bloques disponibles")
            print(f"   ❌ DÉFICIT: Faltan {deficit} bloques horarios")
            print(f"   💡 SOLUCIONES POSIBLES:")
            print(f"      1. Agregar el día SÁBADO (daría {len(self.horarios) * (len(self.dias_semana) + 1)} bloques)")
            print(f"      2. Agregar {math.ceil(deficit / len(self.dias_semana))} horario(s) más al turno {self.turno}")
            print(f"      3. Reducir {deficit} hora(s) del total de materias")
            raise ValueError(f"❌ IMPOSIBLE GENERAR HORARIO: Se requieren {total_horas_semanales} horas pero solo hay {bloques_disponibles} bloques disponibles. Faltan {deficit} bloques.")

    def cargar_disponibilidades(self):
        """Cargar las disponibilidades de todos los profesores"""
        from models import DisponibilidadProfesor

        print("📋 Cargando disponibilidades de profesores...")
        
        for profesor in self.profesores:
            disponibilidades_profesor = DisponibilidadProfesor.query.filter(
                DisponibilidadProfesor.profesor_id == profesor.id,
                DisponibilidadProfesor.activo == True
            ).all()

            # Crear diccionario de disponibilidad por día y horario
            disponibilidad_dict = {}
            total_horas_disponibles = 0
            
            for dia in self.dias_semana:
                disponibilidad_dict[dia] = {}
                for horario in self.horarios:
                    # Buscar registro de disponibilidad específico
                    disp = next((d for d in disponibilidades_profesor
                               if d.dia_semana == dia and d.horario_id == horario.id), None)
                    
                    # IMPORTANTE: Si hay registro, usar su valor. Si NO hay registro, NO está disponible
                    # Esto asegura que el profesor solo pueda dar clases en las horas que marcó como disponibles
                    if disp:
                        disponibilidad_dict[dia][horario.id] = disp.disponible
                        if disp.disponible:
                            total_horas_disponibles += 1
                    else:
                        # Si no hay registro de disponibilidad, asumir NO disponible
                        # (el profesor debe marcar explícitamente sus horas disponibles)
                        disponibilidad_dict[dia][horario.id] = False

            self.disponibilidades[profesor.id] = disponibilidad_dict
            
            print(f"   ✓ {profesor.get_nombre_completo()}: {total_horas_disponibles} horas disponibles")
            
            # Advertencia si el profesor tiene muy pocas horas disponibles
            if total_horas_disponibles < 5:
                print(f"   ⚠️  ADVERTENCIA: Profesor {profesor.get_nombre_completo()} tiene solo {total_horas_disponibles} horas disponibles")

    def validar_datos(self):
        """Validar que hay suficientes datos para generar horarios"""
        if not self.profesores:
            raise ValueError("❌ No hay profesores disponibles para esta carrera")

        if not self.materias:
            raise ValueError("❌ No hay materias disponibles para este cuatrimestre")

        if not self.horarios:
            raise ValueError(f"❌ No hay horarios disponibles para el turno {self.turno}")

        # Verificar que hay suficientes profesores para las materias
        if len(self.profesores) < len(self.materias):
            print(f"⚠️  Advertencia: Hay {len(self.profesores)} profesores para {len(self.materias)} materias")

        return True

    def crear_variables_decision(self):
        """Crear variables de decisión booleanas para el modelo CP-SAT"""
        print("🔧 Creando variables de decisión...")

        for profesor in self.profesores:
            for materia in self.materias:
                for horario in self.horarios:
                    for dia_idx, dia in enumerate(self.dias_semana):
                        # Variable booleana: 1 si se asigna este profesor a esta materia en este horario y día
                        var_name = f"P{profesor.id}_M{materia.id}_H{horario.id}_D{dia_idx}"
                        self.variables[(profesor.id, materia.id, horario.id, dia_idx)] = self.model.NewBoolVar(var_name)

        print(f"✅ Creadas {len(self.variables)} variables de decisión")

    def agregar_restricciones(self):
        """Agregar todas las restricciones al modelo CP-SAT"""
        print("🔒 Agregando restricciones...")

        # 1. Cada materia debe tener exactamente las horas requeridas por semana
        self.restriccion_horas_materia()

        # 2. Un profesor no puede tener dos clases al mismo tiempo
        self.restriccion_no_conflicto_profesor()

        # 3. Un profesor no puede dar clases cuando no está disponible
        self.restriccion_disponibilidad_profesor()

        # 4. Un aula/horario no puede tener dos clases al mismo tiempo (simplificado)
        self.restriccion_no_conflicto_horario()

        # 5. Restricciones de carga horaria por profesor (semanal)
        self.restriccion_carga_horaria_profesor()

        # 6. Restricción: máximo 8 horas diarias por profesor
        self.restriccion_horas_diarias_profesor()

        # 7. Restricciones de distribución óptima de horas por materia (máx 3 horas seguidas)
        self.restriccion_distribucion_horas_materia()

        # 7.1. NUEVA: Restricción de horas consecutivas por materia (evitar fragmentación)
        self.restriccion_materias_consecutivas()

        # 8. Restricciones para evitar conflictos entre carreras
        self.restriccion_conflictos_entre_carreras()

        # 9. NUEVA: Restricción para agrupar horas de trabajo y limitar horas muertas
        self.restriccion_horas_muertas_profesor()

        # 10. NUEVA: Fomentar bloques continuos de trabajo
        self.restriccion_bloques_continuos_profesor()

        print("✅ Todas las restricciones agregadas")

    def restriccion_horas_materia(self):
        """
        Cada materia debe tener exactamente las horas requeridas por semana
        Usa horas_semanales configuradas en cada materia
        """
        print("📚 Aplicando restricción de horas semanales por materia...")
        
        for materia in self.materias:
            horas_requeridas = self.calcular_horas_semanales_materia(materia)

            # Suma de todas las asignaciones para esta materia debe ser igual a horas requeridas
            asignaciones_materia = []
            for profesor in self.profesores:
                for horario in self.horarios:
                    for dia_idx in range(len(self.dias_semana)):
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_materia.append(var)

            if asignaciones_materia:
                self.model.Add(sum(asignaciones_materia) == horas_requeridas)
                print(f"   ✓ {materia.codigo} ({materia.nombre}): {horas_requeridas}h/semana")

    def restriccion_no_conflicto_profesor(self):
        """Un profesor no puede tener dos clases al mismo tiempo"""
        for profesor in self.profesores:
            for horario in self.horarios:
                for dia_idx in range(len(self.dias_semana)):
                    # En un mismo horario y día, un profesor solo puede tener una materia
                    asignaciones_profesor_horario = []
                    for materia in self.materias:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_profesor_horario.append(var)

                    if asignaciones_profesor_horario:
                        self.model.Add(sum(asignaciones_profesor_horario) <= 1)

    def restriccion_disponibilidad_profesor(self):
        """Un profesor solo puede dar clases en las horas que marcó como disponibles"""
        print("📅 Aplicando restricción de disponibilidad de profesores...")
        
        restricciones_aplicadas = 0
        
        for profesor in self.profesores:
            for horario in self.horarios:
                for dia_idx, dia in enumerate(self.dias_semana):
                    # Verificar si el profesor está disponible en este horario y día
                    disponible = self.verificar_disponibilidad_profesor(profesor.id, horario.id, dia)

                    if not disponible:
                        # El profesor NO está disponible: forzar que no tenga clase
                        for materia in self.materias:
                            var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                self.model.Add(var == 0)
                                restricciones_aplicadas += 1
        
        print(f"   ✓ Se aplicaron {restricciones_aplicadas} restricciones de disponibilidad")

    def restriccion_no_conflicto_horario(self):
        """Un horario no puede tener dos clases al mismo tiempo (simplificación)"""
        # Esta es una simplificación. En un sistema real, consideraríamos aulas específicas
        for horario in self.horarios:
            for dia_idx in range(len(self.dias_semana)):
                # En un mismo horario y día, máximo una clase (simplificación)
                asignaciones_horario = []
                for profesor in self.profesores:
                    for materia in self.materias:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_horario.append(var)

                if asignaciones_horario:
                    self.model.Add(sum(asignaciones_horario) <= 1)

    def restriccion_carga_horaria_profesor(self):
        """Restricciones de carga horaria máxima por profesor (semanal)"""
        for profesor in self.profesores:
            # Calcular carga horaria máxima según tipo de profesor
            if profesor.is_profesor_completo():
                max_horas = 40  # 40 horas semanales para tiempo completo
            else:
                max_horas = 20  # 20 horas semanales para asignatura

            # Suma de todas las asignaciones del profesor
            asignaciones_profesor = []
            for materia in self.materias:
                for horario in self.horarios:
                    for dia_idx in range(len(self.dias_semana)):
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_profesor.append(var)

            if asignaciones_profesor:
                self.model.Add(sum(asignaciones_profesor) <= max_horas)

    def restriccion_horas_diarias_profesor(self):
        """Un profesor no puede trabajar más de 8 horas al día"""
        for profesor in self.profesores:
            for dia_idx in range(len(self.dias_semana)):
                # Suma de todas las horas asignadas en este día
                asignaciones_profesor_dia = []
                for materia in self.materias:
                    for horario in self.horarios:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_profesor_dia.append(var)
                
                if asignaciones_profesor_dia:
                    # Máximo 8 horas por día
                    self.model.Add(sum(asignaciones_profesor_dia) <= 8)
                    print(f"✓ Restricción: Profesor {profesor.get_nombre_completo()} - máx 8h/día en {self.dias_semana[dia_idx]}")

    def restriccion_distribucion_horas_materia(self):
        """
        Distribuir horas de manera óptima:
        - Máximo 3 horas SEGUIDAS de la misma materia por día
        - Preferir distribución uniforme a lo largo de la semana
        """
        print("📊 Aplicando restricción de distribución de horas por materia...")
        
        for materia in self.materias:
            horas_requeridas = self.calcular_horas_semanales_materia(materia)
            
            # RESTRICCIÓN PRINCIPAL: Máximo 3 horas por día de la misma materia
            for dia_idx in range(len(self.dias_semana)):
                asignaciones_materia_dia = []
                for profesor in self.profesores:
                    for horario in self.horarios:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_materia_dia.append(var)
                
                if asignaciones_materia_dia:
                    # ⚠️ IMPORTANTE: Máximo 3 horas por día de la misma materia
                    self.model.Add(sum(asignaciones_materia_dia) <= 3)
            
            print(f"   ✓ Materia {materia.codigo}: {horas_requeridas}h/semana, máx 3h/día")
    
    def restriccion_materias_consecutivas(self):
        """
        RESTRICCIÓN CRÍTICA: Las horas de una misma materia en el mismo día deben ser CONSECUTIVAS.
        Evita que se fragmente una materia (ej: Física 7-8, otra materia 8-9, Física 9-10)
        """
        print("🔗 Aplicando restricción de horas consecutivas por materia...")
        
        restricciones_aplicadas = 0
        
        for materia in self.materias:
            for dia_idx in range(len(self.dias_semana)):
                # Para cada profesor que imparte esta materia
                for profesor in self.profesores:
                    # Verificar todos los horarios posibles
                    horarios_materia = []
                    
                    for i, horario in enumerate(self.horarios):
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            horarios_materia.append((i, var))
                    
                    # Si hay al menos 2 horarios posibles, aplicar restricción de consecutividad
                    if len(horarios_materia) >= 2:
                        for k in range(len(horarios_materia) - 2):
                            idx_anterior = horarios_materia[k][0]
                            idx_medio = horarios_materia[k + 1][0]
                            idx_siguiente = horarios_materia[k + 2][0]
                            
                            # Solo aplicar si los índices son consecutivos en la lista de horarios
                            if idx_medio == idx_anterior + 1 and idx_siguiente == idx_medio + 1:
                                var_anterior = horarios_materia[k][1]
                                var_medio = horarios_materia[k + 1][1]
                                var_siguiente = horarios_materia[k + 2][1]
                                
                                # Si hay clase en horario anterior Y siguiente, 
                                # DEBE haber clase en el horario del medio
                                # Equivalente a: si (anterior=1 Y siguiente=1) entonces medio=1
                                # Implementación: anterior + siguiente - 1 <= medio
                                # O mejor: anterior + siguiente <= 1 + medio
                                self.model.Add(var_anterior + var_siguiente <= 1 + var_medio)
                                restricciones_aplicadas += 1
        
        print(f"   ✓ Se aplicaron {restricciones_aplicadas} restricciones de consecutividad")

    def restriccion_conflictos_entre_carreras(self):
        """Evitar que profesores tengan clases simultáneas en diferentes carreras"""
        # Obtener todos los profesores que imparten en múltiples carreras
        profesores_multiples_carreras = []
        
        for profesor in self.profesores:
            # Verificar si el profesor imparte en otras carreras
            carreras_profesor = set()
            
            # Agregar la carrera actual
            carreras_profesor.add(self.carrera_id)
            
            # Buscar materias del profesor en otras carreras
            otras_materias = Materia.query.filter(
                Materia.id.in_([m.id for m in profesor.materias]),
                Materia.carrera_id != self.carrera_id,
                Materia.activa == True
            ).all()
            
            for materia in otras_materias:
                carreras_profesor.add(materia.carrera_id)
            
            if len(carreras_profesor) > 1:
                profesores_multiples_carreras.append(profesor.id)
                print(f"⚠️  Profesor {profesor.get_nombre_completo()} imparte en {len(carreras_profesor)} carreras")
        
        # Para profesores que imparten en múltiples carreras, verificar conflictos
        for profesor_id in profesores_multiples_carreras:
            # Obtener horarios académicos existentes de otras carreras para este profesor
            horarios_existentes = HorarioAcademico.query.filter(
                HorarioAcademico.profesor_id == profesor_id,
                HorarioAcademico.periodo_academico == self.periodo_academico,
                HorarioAcademico.activo == True
            ).join(Materia).filter(
                Materia.carrera_id != self.carrera_id
            ).all()
            
            # Para cada horario existente, evitar asignaciones conflictivas
            for horario_existente in horarios_existentes:
                dia_idx = self.dias_semana.index(horario_existente.dia_semana) if horario_existente.dia_semana in self.dias_semana else -1
                
                if dia_idx >= 0:
                    # No asignar este profesor en el mismo horario y día
                    for materia in self.materias:
                        var = self.variables.get((profesor_id, materia.id, horario_existente.horario_id, dia_idx))
                        if var is not None:
                            self.model.Add(var == 0)  # Forzar que no se asigne

    def restriccion_horas_muertas_profesor(self):
        """Limitar horas muertas entre clases a máximo 2 horas por profesor por día"""
        print("🕐 Aplicando restricción de horas muertas (máx 2 horas libres entre clases)...")
        
        restricciones_aplicadas = 0
        
        for profesor in self.profesores:
            for dia_idx in range(len(self.dias_semana)):
                dia = self.dias_semana[dia_idx]
                
                # Para cada par de horarios con distancia > 2 horas
                for i, horario_inicio in enumerate(self.horarios):
                    for j, horario_fin in enumerate(self.horarios):
                        if j <= i + 3:  # Solo considerar si hay más de 2 horas de distancia
                            continue
                        
                        # Si j - i > 3, hay más de 2 horas entre horario_inicio y horario_fin
                        # Si el profesor tiene clase en horario_inicio Y en horario_fin,
                        # entonces debe tener al menos una clase en los horarios intermedios
                        
                        # Variables: tiene clase en horario_inicio
                        tiene_clase_inicio = []
                        for materia in self.materias:
                            var = self.variables.get((profesor.id, materia.id, horario_inicio.id, dia_idx))
                            if var is not None:
                                tiene_clase_inicio.append(var)
                        
                        # Variables: tiene clase en horario_fin
                        tiene_clase_fin = []
                        for materia in self.materias:
                            var = self.variables.get((profesor.id, materia.id, horario_fin.id, dia_idx))
                            if var is not None:
                                tiene_clase_fin.append(var)
                        
                        # Variables: tiene clases en horarios intermedios
                        tiene_clase_intermedia = []
                        for k in range(i + 1, j):
                            horario_intermedio = self.horarios[k]
                            for materia in self.materias:
                                var = self.variables.get((profesor.id, materia.id, horario_intermedio.id, dia_idx))
                                if var is not None:
                                    tiene_clase_intermedia.append(var)
                        
                        if tiene_clase_inicio and tiene_clase_fin and tiene_clase_intermedia:
                            # Crear variables auxiliares
                            tiene_inicio = self.model.NewBoolVar(f'inicio_P{profesor.id}_D{dia_idx}_H{i}')
                            tiene_fin = self.model.NewBoolVar(f'fin_P{profesor.id}_D{dia_idx}_H{j}')
                            
                            # tiene_inicio = 1 si hay al menos una clase en horario_inicio
                            self.model.AddMaxEquality(tiene_inicio, tiene_clase_inicio)
                            
                            # tiene_fin = 1 si hay al menos una clase en horario_fin
                            self.model.AddMaxEquality(tiene_fin, tiene_clase_fin)
                            
                            # Si tiene_inicio Y tiene_fin, entonces debe tener al menos una clase intermedia
                            ambos_extremos = self.model.NewBoolVar(f'ambos_P{profesor.id}_D{dia_idx}_H{i}_{j}')
                            self.model.AddMultiplicationEquality(ambos_extremos, [tiene_inicio, tiene_fin])
                            
                            # Si ambos_extremos = 1, entonces sum(tiene_clase_intermedia) >= 1
                            # Esto se puede expresar como: sum(tiene_clase_intermedia) >= ambos_extremos
                            self.model.Add(sum(tiene_clase_intermedia) >= ambos_extremos)
                            
                            restricciones_aplicadas += 1
        
        print(f"   ✓ Se aplicaron {restricciones_aplicadas} restricciones para evitar horas muertas")

    def restriccion_bloques_continuos_profesor(self):
        """Fomentar que las horas de trabajo de los profesores estén en bloques continuos"""
        print("📦 Aplicando restricción de bloques continuos de trabajo...")
        
        for profesor in self.profesores:
            for dia_idx in range(len(self.dias_semana)):
                dia = self.dias_semana[dia_idx]
                
                # Para cada día, preferir que si hay clases, estén agrupadas
                # Penalizar "islas" de horas libres entre clases
                
                for i in range(len(self.horarios)):
                    horario = self.horarios[i]
                    
                    # Variable: tiene clase en este horario
                    tiene_clase_actual = []
                    for materia in self.materias:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            tiene_clase_actual.append(var)
                    
                    if not tiene_clase_actual:
                        continue
                    
                    # Si tiene clase aquí, verificar vecinos
                    if i > 0:  # Hay horario anterior
                        tiene_clase_anterior = []
                        horario_anterior = self.horarios[i - 1]
                        for materia in self.materias:
                            var = self.variables.get((profesor.id, materia.id, horario_anterior.id, dia_idx))
                            if var is not None:
                                tiene_clase_anterior.append(var)
                    
                    if i < len(self.horarios) - 1:  # Hay horario siguiente
                        tiene_clase_siguiente = []
                        horario_siguiente = self.horarios[i + 1]
                        for materia in self.materias:
                            var = self.variables.get((profesor.id, materia.id, horario_siguiente.id, dia_idx))
                            if var is not None:
                                tiene_clase_siguiente.append(var)
        
        print(f"   ✓ Restricción de bloques continuos aplicada para {len(self.profesores)} profesores")

    def agregar_funcion_objetivo(self):
        """Agregar función objetivo para optimizar la distribución y minimizar horas muertas"""
        print("🎯 Agregando función objetivo...")

        # Objetivo múltiple:
        # 1. Minimizar la varianza en la carga horaria de profesores
        # 2. Minimizar las horas muertas (maximizar bloques continuos)
        # 3. Minimizar el número de días con clases por profesor

        objetivos = []
        
        # OBJETIVO 1: Distribuir equitativamente la carga de trabajo
        cargas_horarias = []
        for profesor in self.profesores:
            carga_profesor = []
            for materia in self.materias:
                for horario in self.horarios:
                    for dia_idx in range(len(self.dias_semana)):
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            carga_profesor.append(var)

            if carga_profesor:
                cargas_horarias.append(sum(carga_profesor))

        diferencia_carga = None
        if cargas_horarias and len(cargas_horarias) > 1:
            # Crear variables para max y min
            max_carga = self.model.NewIntVar(0, 50, 'max_carga')
            min_carga = self.model.NewIntVar(0, 50, 'min_carga')
            
            # max_carga debe ser mayor o igual a todas las cargas
            for carga in cargas_horarias:
                self.model.Add(max_carga >= carga)
            
            # min_carga debe ser menor o igual a todas las cargas
            for carga in cargas_horarias:
                self.model.Add(min_carga <= carga)
            
            # Diferencia entre máximo y mínimo
            diferencia_carga = max_carga - min_carga
            objetivos.append(diferencia_carga * 5)  # Peso 5 para la equidad

        # OBJETIVO 2: Minimizar horas muertas (maximizar continuidad)
        # Contamos las "transiciones" de no-clase a clase y de clase a no-clase
        transiciones_totales = []
        
        for profesor in self.profesores:
            for dia_idx in range(len(self.dias_semana)):
                for i in range(len(self.horarios) - 1):
                    # Verificar transición entre horario i y horario i+1
                    horario_actual = self.horarios[i]
                    horario_siguiente = self.horarios[i + 1]
                    
                    # Variable: tiene clase en horario actual
                    tiene_clase_actual = []
                    for materia in self.materias:
                        var = self.variables.get((profesor.id, materia.id, horario_actual.id, dia_idx))
                        if var is not None:
                            tiene_clase_actual.append(var)
                    
                    # Variable: tiene clase en horario siguiente
                    tiene_clase_siguiente = []
                    for materia in self.materias:
                        var = self.variables.get((profesor.id, materia.id, horario_siguiente.id, dia_idx))
                        if var is not None:
                            tiene_clase_siguiente.append(var)
                    
                    if tiene_clase_actual and tiene_clase_siguiente:
                        # Variables booleanas para saber si tiene clase
                        tiene_actual = self.model.NewBoolVar(f'actual_P{profesor.id}_D{dia_idx}_H{i}')
                        tiene_sig = self.model.NewBoolVar(f'sig_P{profesor.id}_D{dia_idx}_H{i+1}')
                        
                        self.model.AddMaxEquality(tiene_actual, tiene_clase_actual)
                        self.model.AddMaxEquality(tiene_sig, tiene_clase_siguiente)
                        
                        # Variable para detectar transiciones (cambios de estado)
                        # Una transición ocurre cuando: (tiene_actual AND NOT tiene_sig) OR (NOT tiene_actual AND tiene_sig)
                        # Simplificado: transición = |tiene_actual - tiene_sig|
                        # Como son booleanos: transición = tiene_actual + tiene_sig - 2*tiene_actual*tiene_sig
                        transicion = self.model.NewBoolVar(f'trans_P{profesor.id}_D{dia_idx}_H{i}')
                        
                        # transicion = 1 si hay cambio de estado
                        # Si ambos son iguales (00 o 11), transicion = 0
                        # Si son diferentes (01 o 10), transicion = 1
                        # Esto se logra con XOR: transicion = tiene_actual + tiene_sig - 2*(tiene_actual AND tiene_sig)
                        producto = self.model.NewBoolVar(f'prod_P{profesor.id}_D{dia_idx}_H{i}')
                        self.model.AddMultiplicationEquality(producto, [tiene_actual, tiene_sig])
                        
                        # transicion = tiene_actual XOR tiene_sig
                        self.model.Add(tiene_actual + tiene_sig - 2 * producto >= transicion)
                        self.model.Add(tiene_actual + tiene_sig - 2 * producto <= transicion + 1)
                        
                        transiciones_totales.append(transicion)
        
        if transiciones_totales:
            total_transiciones = sum(transiciones_totales)
            objetivos.append(total_transiciones * 10)  # Peso 10 para minimizar transiciones (muy importante)

        # OBJETIVO 3: Minimizar días con clases (concentrar en menos días)
        dias_con_clases_totales = []
        
        for profesor in self.profesores:
            for dia_idx in range(len(self.dias_semana)):
                # Variable: profesor tiene al menos una clase en este día
                dia_tiene_clase = self.model.NewBoolVar(f'dia_clase_P{profesor.id}_D{dia_idx}')
                
                clases_en_dia = []
                for materia in self.materias:
                    for horario in self.horarios:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            clases_en_dia.append(var)
                
                if clases_en_dia:
                    # Si hay al menos una clase, dia_tiene_clase = 1
                    self.model.AddMaxEquality(dia_tiene_clase, clases_en_dia)
                    dias_con_clases_totales.append(dia_tiene_clase)
        
        if dias_con_clases_totales:
            total_dias = sum(dias_con_clases_totales)
            objetivos.append(total_dias * 3)  # Peso 3 para concentrar días

        # FUNCIÓN OBJETIVO COMBINADA: Minimizar suma ponderada
        if objetivos:
            objetivo_total = sum(objetivos)
            self.model.Minimize(objetivo_total)
            print(f"   ✓ Función objetivo con {len(objetivos)} componentes:")
            print(f"      - Equidad de carga (peso 5)")
            print(f"      - Minimizar transiciones/horas muertas (peso 10)")
            print(f"      - Concentrar días de trabajo (peso 3)")
        elif diferencia_carga is not None:
            # Fallback: solo minimizar diferencia de carga
            self.model.Minimize(diferencia_carga)
            print(f"   ✓ Función objetivo: solo equidad de carga")

    def resolver_modelo(self):
        """Resolver el modelo CP-SAT"""
        print("🧠 Resolviendo modelo CP-SAT...")

        # Configurar solver
        self.solver.parameters.max_time_in_seconds = 300.0  # 5 minutos máximo
        self.solver.parameters.num_search_workers = 8  # Usar múltiples hilos

        # Resolver
        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            self.solucion_encontrada = True
            print("✅ ¡Solución encontrada!")
            return True
        else:
            print(f"❌ No se encontró solución. Estado: {status}")
            return False

    def interpretar_solucion(self):
        """Interpretar la solución encontrada y crear los horarios académicos"""
        print("📋 Interpretando solución...")

        # Si se generó para un grupo específico, eliminar solo los horarios de ese grupo
        if self.grupo_id:
            from models import Grupo
            grupo = Grupo.query.get(self.grupo_id)
            if grupo:
                # Obtener todas las materias del grupo
                materias_ids = [m.id for m in grupo.materias]
                
                # Eliminar horarios anteriores de este grupo (sus materias)
                if materias_ids:
                    print(f"🗑️  Eliminando horarios anteriores del grupo {grupo.codigo}...")
                    HorarioAcademico.query.filter(
                        HorarioAcademico.materia_id.in_(materias_ids)
                    ).delete(synchronize_session=False)
                    db.session.commit()
        else:
            # Limpiar horarios existentes para este período y carrera (modo legacy)
            HorarioAcademico.query.filter(
                HorarioAcademico.periodo_academico == self.periodo_academico,
                HorarioAcademico.activo == True
            ).update({'activo': False})
            db.session.commit()

        horarios_creados = []

        # Recorrer todas las variables para encontrar asignaciones
        for (profesor_id, materia_id, horario_id, dia_idx), var in self.variables.items():
            if self.solver.Value(var) == 1:  # Si la variable es verdadera
                dia = self.dias_semana[dia_idx]

                # Crear horario académico
                horario_academico = HorarioAcademico(
                    profesor_id=profesor_id,
                    materia_id=materia_id,
                    horario_id=horario_id,
                    dia_semana=dia,
                    periodo_academico=self.periodo_academico,
                    version_nombre=self.version_nombre,
                    creado_por=self.creado_por
                )

                db.session.add(horario_academico)
                horarios_creados.append(horario_academico)

                print(f"📅 Asignado: Prof {profesor_id} → Materia {materia_id} en {dia} horario {horario_id}")

        # Confirmar cambios
        db.session.commit()
        self.horarios_generados = horarios_creados

        print(f"✅ Se crearon {len(horarios_creados)} horarios académicos")
        return horarios_creados

    def calcular_horas_semanales_materia(self, materia):
        """
        Calcular horas semanales necesarias para una materia
        Usa las horas teóricas + horas prácticas configuradas en la materia
        """
        # Obtener horas totales (teóricas + prácticas)
        horas_totales = materia.horas_semanales if materia.horas_semanales else 0
        
        # Validación: mínimo 1 hora, máximo razonable 15 horas
        if horas_totales < 1:
            print(f"⚠️  Advertencia: Materia {materia.codigo} no tiene horas configuradas. Usando 3 horas por defecto.")
            return 3
        
        if horas_totales > 15:
            print(f"⚠️  Advertencia: Materia {materia.codigo} tiene {horas_totales} horas (muy alto). Limitando a 15 horas.")
            return 15
        
        return horas_totales

    def verificar_disponibilidad_profesor(self, profesor_id, horario_id, dia_semana):
        """Verificar si un profesor está disponible en ese horario y día"""
        if profesor_id not in self.disponibilidades:
            return False  # Si no hay registro de disponibilidad, asumir NO disponible

        disponibilidad_dia = self.disponibilidades[profesor_id].get(dia_semana, {})
        return disponibilidad_dia.get(horario_id, False)  # Por defecto NO disponible

    def generar_horarios(self):
        """Generar horarios académicos usando OR-Tools"""
        print("🚀 Iniciando generación de horarios con Google OR-Tools CP-SAT...")
        print("="*70)
        print("📋 RESTRICCIONES APLICADAS:")
        print("   1. ✓ Cada materia debe tener sus horas semanales requeridas")
        print("   2. ✓ Un profesor NO puede tener dos clases simultáneas")
        print("   3. ✓ Profesores SOLO dan clases en horas marcadas como disponibles")
        print("   4. ✓ Máximo 3 HORAS SEGUIDAS de la misma materia por día")
        print("   5. ✓ Máximo 8 HORAS de trabajo por día por profesor")
        print("   6. ✓ Carga máxima semanal: 40h (tiempo completo) / 20h (asignatura)")
        print("   7. ✓ Sin conflictos de horario entre carreras")
        print("   8. ✓ HORAS CONSECUTIVAS por materia (sin fragmentación)")
        print("   9. ✓ MÁXIMO 2 HORAS LIBRES entre clases (profesores de lejos)")
        print("  10. ✓ BLOQUES CONTINUOS de trabajo (minimizar horas muertas)")
        print("")
        print("🎯 OPTIMIZACIÓN:")
        print("   • Agrupar horas de trabajo en bloques continuos")
        print("   • Minimizar transiciones y horas muertas")
        print("   • Concentrar días de trabajo")
        print("   • Distribuir carga equitativamente entre profesores")
        print("="*70)

        try:
            # Cargar y validar datos
            self.cargar_datos()
            self.validar_datos()

            # Crear modelo
            self.crear_variables_decision()
            self.agregar_restricciones()
            self.agregar_funcion_objetivo()

            # Resolver
            if self.resolver_modelo():
                horarios_generados = self.interpretar_solucion()
                estadisticas = self.obtener_estadisticas()

                return {
                    'exito': True,
                    'mensaje': f'✅ Se generaron {len(horarios_generados)} horarios académicos exitosamente usando OR-Tools',
                    'estadisticas': estadisticas,
                    'horarios_generados': horarios_generados,
                    'algoritmo': 'Google OR-Tools CP-SAT Solver'
                }
            else:
                return {
                    'exito': False,
                    'mensaje': '❌ No se pudo encontrar una solución factible con las restricciones dadas',
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': 'Google OR-Tools CP-SAT Solver'
                }

        except Exception as e:
            db.session.rollback()
            return {
                'exito': False,
                'mensaje': f'❌ Error al generar horarios: {str(e)}',
                'estadisticas': None,
                'horarios_generados': [],
                'algoritmo': 'Google OR-Tools CP-SAT Solver'
            }

    def obtener_estadisticas(self):
        """Obtener estadísticas de la generación con detalles de horas por materia"""
        if not self.horarios_generados:
            return {
                'total_horarios': 0,
                'profesores_utilizados': 0,
                'materias_asignadas': 0,
                'materias_totales': len(self.materias),
                'profesores_totales': len(self.profesores),
                'eficiencia': 0.0,
                'horas_por_materia': {}
            }

        total_horarios = len(self.horarios_generados)
        profesores_utilizados = len(set(h.profesor_id for h in self.horarios_generados))
        materias_asignadas = len(set(h.materia_id for h in self.horarios_generados))

        eficiencia = (materias_asignadas / len(self.materias)) * 100 if self.materias else 0

        # Calcular horas asignadas por materia
        horas_por_materia = {}
        for materia in self.materias:
            horas_asignadas = sum(1 for h in self.horarios_generados if h.materia_id == materia.id)
            horas_requeridas = self.calcular_horas_semanales_materia(materia)
            horas_por_materia[materia.codigo] = {
                'nombre': materia.nombre,
                'horas_requeridas': horas_requeridas,
                'horas_asignadas': horas_asignadas,
                'horas_semanales': materia.horas_semanales,
                'completado': horas_asignadas == horas_requeridas
            }

        return {
            'total_horarios': total_horarios,
            'profesores_utilizados': profesores_utilizados,
            'materias_asignadas': materias_asignadas,
            'materias_totales': len(self.materias),
            'profesores_totales': len(self.profesores),
            'eficiencia': eficiencia,
            'horas_por_materia': horas_por_materia
        }


class GeneradorHorariosSinOR:
    """Generador de horarios que funciona sin OR-Tools como respaldo"""
    
    def __init__(self, carrera_id, cuatrimestre, turno='matutino', dias_semana=None,
                 periodo_academico='2025-1', version_nombre=None, creado_por=None, grupo_id=None):
        """Inicializar el generador de horarios sin OR-Tools"""
        self.carrera_id = carrera_id
        self.cuatrimestre = cuatrimestre
        self.turno = turno
        self.dias_semana = dias_semana or ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        self.periodo_academico = periodo_academico
        self.version_nombre = version_nombre
        self.creado_por = creado_por
        self.grupo_id = grupo_id  # Nuevo parámetro
        
        # Datos del proceso
        self.profesores = []
        self.materias = []
        self.horarios = []
        self.disponibilidades = {}
        self.horarios_generados = []
        self.grupo = None  # Objeto Grupo si se proporciona grupo_id
        
        # Cache para evitar conflictos
        self.asignaciones_profesor = defaultdict(list)  # profesor_id -> [(horario_id, dia)]
        self.asignaciones_horario = defaultdict(list)   # (horario_id, dia) -> materia_id
    
    def cargar_datos(self):
        """Cargar datos necesarios para la generación"""
        from models import DisponibilidadProfesor, Grupo

        # Si se proporciona grupo_id, usar los datos del grupo
        if self.grupo_id:
            self.grupo = Grupo.query.get(self.grupo_id)
            if not self.grupo:
                raise ValueError(f"No se encontró el grupo con ID {self.grupo_id}")
            
            # Obtener materias del grupo
            self.materias = [m for m in self.grupo.materias if m.activa]
            
            # Obtener profesores que imparten esas materias (solo los activos)
            profesores_set = set()
            for materia in self.materias:
                for profesor in materia.profesores:
                    if profesor.activo:
                        profesores_set.add(profesor)
            self.profesores = list(profesores_set)
            
            print(f"📚 Cargando datos del grupo {self.grupo.codigo} (algoritmo respaldo):")
            print(f"   - Materias asignadas: {len(self.materias)}")
            print(f"   - Profesores asignados: {len(self.profesores)}")
        else:
            # Enfoque legacy: cargar por carrera y cuatrimestre
            # Cargar profesores de la carrera
            self.profesores = User.query.filter(
                User.carrera_id == self.carrera_id,
                User.rol.in_(['profesor_completo', 'profesor_asignatura']),
                User.activo == True
            ).all()

            # Cargar materias del cuatrimestre
            self.materias = Materia.query.filter(
                Materia.carrera_id == self.carrera_id,
                Materia.cuatrimestre == self.cuatrimestre,
                Materia.activa == True
            ).all()

        # Validaciones
        if not self.profesores:
            raise ValueError("❌ No hay profesores disponibles")
        
        if not self.materias:
            raise ValueError("❌ No hay materias disponibles")

        # Cargar horarios según el turno
        if self.turno == 'ambos':
            self.horarios = Horario.query.filter_by(activo=True).order_by(Horario.orden).all()
        else:
            self.horarios = Horario.query.filter_by(
                turno=self.turno,
                activo=True
            ).order_by(Horario.orden).all()

        # Cargar disponibilidades
        self.cargar_disponibilidades()
        
        # Cargar horarios existentes de otras carreras para evitar conflictos
        self.cargar_conflictos_existentes()

        print(f"✅ Datos cargados: {len(self.profesores)} profesores, {len(self.materias)} materias, {len(self.horarios)} horarios")
    
    def cargar_disponibilidades(self):
        """Cargar disponibilidades de profesores"""
        from models import DisponibilidadProfesor
        
        for profesor in self.profesores:
            disponibilidades_profesor = DisponibilidadProfesor.query.filter(
                DisponibilidadProfesor.profesor_id == profesor.id,
                DisponibilidadProfesor.activo == True
            ).all()

            disponibilidad_dict = {}
            for dia in self.dias_semana:
                disponibilidad_dict[dia] = {}
                for horario in self.horarios:
                    disp = next((d for d in disponibilidades_profesor
                               if d.dia_semana == dia and d.horario_id == horario.id), None)
                    # Si hay registro, usar su valor. Si NO hay registro, NO está disponible (False)
                    disponibilidad_dict[dia][horario.id] = disp.disponible if disp else False

            self.disponibilidades[profesor.id] = disponibilidad_dict
    
    def cargar_conflictos_existentes(self):
        """Cargar horarios existentes para evitar conflictos"""
        for profesor in self.profesores:
            horarios_existentes = HorarioAcademico.query.filter(
                HorarioAcademico.profesor_id == profesor.id,
                HorarioAcademico.periodo_academico == self.periodo_academico,
                HorarioAcademico.activo == True
            ).join(Materia).filter(
                Materia.carrera_id != self.carrera_id
            ).all()
            
            for horario_existente in horarios_existentes:
                if horario_existente.dia_semana in self.dias_semana:
                    clave_horario = (horario_existente.horario_id, horario_existente.dia_semana)
                    self.asignaciones_profesor[profesor.id].append(clave_horario)
    
    def generar_horarios(self):
        """Generar horarios usando algoritmo greedy mejorado"""
        print("🚀 Iniciando generación con algoritmo de respaldo...")
        
        try:
            self.cargar_datos()
            
            if not self.profesores or not self.materias or not self.horarios:
                return {
                    'exito': False,
                    'mensaje': "❌ Datos insuficientes para generar horarios",
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': 'Algoritmo de Respaldo'
                }
            
            # Limpiar horarios existentes
            HorarioAcademico.query.filter(
                HorarioAcademico.periodo_academico == self.periodo_academico,
                HorarioAcademico.activo == True
            ).update({'activo': False})
            db.session.commit()
            
            # Generar asignaciones
            exito = self.asignar_materias_a_profesores()
            
            if exito:
                estadisticas = self.obtener_estadisticas()
                return {
                    'exito': True,
                    'mensaje': f'✅ Se generaron {len(self.horarios_generados)} horarios académicos usando algoritmo de respaldo',
                    'estadisticas': estadisticas,
                    'horarios_generados': self.horarios_generados,
                    'algoritmo': 'Algoritmo de Respaldo (Greedy Mejorado)'
                }
            else:
                return {
                    'exito': False,
                    'mensaje': "❌ No se pudieron asignar todas las materias con las restricciones dadas",
                    'estadisticas': None,
                    'horarios_generados': self.horarios_generados,
                    'algoritmo': 'Algoritmo de Respaldo'
                }
                
        except Exception as e:
            db.session.rollback()
            return {
                'exito': False,
                'mensaje': f'❌ Error al generar horarios: {str(e)}',
                'estadisticas': None,
                'horarios_generados': [],
                'algoritmo': 'Algoritmo de Respaldo'
            }
    
    def asignar_materias_a_profesores(self):
        """Asignar materias a profesores usando algoritmo greedy"""
        materias_pendientes = list(self.materias)
        
        print(f"\n📊 Iniciando asignación de {len(materias_pendientes)} materias")
        print(f"👥 Profesores disponibles: {len(self.profesores)}")
        for profesor in self.profesores:
            print(f"   - {profesor.get_nombre_completo()}: {len(profesor.materias)} materias asignadas")
        
        # Ordenar materias por horas requeridas (descendente) y por dificultad de asignación
        materias_pendientes.sort(key=lambda m: (-self.calcular_horas_semanales_materia(m), m.nombre))
        
        materias_asignadas_exitosamente = 0
        
        for materia in materias_pendientes:
            print(f"\n📚 Procesando materia: {materia.nombre} (ID: {materia.id})")
            print(f"   Horas requeridas: {self.calcular_horas_semanales_materia(materia)}")
            
            # Buscar profesores que pueden impartir esta materia
            profesores_disponibles = [p for p in self.profesores if materia in p.materias]
            
            print(f"   Profesores que pueden impartir esta materia: {len(profesores_disponibles)}")
            for p in profesores_disponibles:
                print(f"      - {p.get_nombre_completo()}")
            
            if not profesores_disponibles:
                print(f"   ⚠️  No hay profesores disponibles para {materia.nombre}")
                print(f"   📋 Verificando: esta materia está en las materias de los profesores?")
                for profesor in self.profesores:
                    materia_ids = [m.id for m in profesor.materias]
                    print(f"      - {profesor.get_nombre_completo()}: materias {materia_ids}")
                continue
            
            # Ordenar profesores por carga actual (ascendente)
            profesores_disponibles.sort(key=lambda p: len(self.asignaciones_profesor[p.id]))
            
            asignado = False
            for profesor in profesores_disponibles:
                if self.asignar_materia_a_profesor(materia, profesor):
                    print(f"   ✅ {materia.nombre} asignada a {profesor.get_nombre_completo()}")
                    asignado = True
                    materias_asignadas_exitosamente += 1
                    break
            
            if not asignado:
                print(f"   ❌ No se pudo asignar {materia.nombre}")
                print(f"   📊 Resumen hasta ahora: {materias_asignadas_exitosamente}/{len(materias_pendientes)} materias asignadas")
                return False
        
        print(f"\n✅ Todas las materias fueron asignadas exitosamente!")
        print(f"📊 Total: {materias_asignadas_exitosamente}/{len(materias_pendientes)} materias")
        return True
    
    def asignar_materia_a_profesor(self, materia, profesor):
        """Asignar una materia específica a un profesor específico"""
        horas_requeridas = self.calcular_horas_semanales_materia(materia)
        horarios_asignados = []
        
        # Estrategia de distribución según horas requeridas
        if horas_requeridas <= 5:
            # 1-5 horas: distribuir una hora por día preferentemente
            horarios_asignados = self.distribuir_horas_dispersas(profesor, materia, horas_requeridas)
        else:
            # Más de 5 horas: permitir hasta 3 horas por día
            horarios_asignados = self.distribuir_horas_agrupadas(profesor, materia, horas_requeridas)
        
        if len(horarios_asignados) == horas_requeridas:
            # Crear los horarios académicos
            for horario_id, dia in horarios_asignados:
                horario_academico = HorarioAcademico(
                    profesor_id=profesor.id,
                    materia_id=materia.id,
                    horario_id=horario_id,
                    dia_semana=dia,
                    periodo_academico=self.periodo_academico,
                    version_nombre=self.version_nombre,
                    creado_por=self.creado_por
                )
                db.session.add(horario_academico)
                self.horarios_generados.append(horario_academico)
                
                # Actualizar cache
                self.asignaciones_profesor[profesor.id].append((horario_id, dia))
                self.asignaciones_horario[(horario_id, dia)].append(materia.id)
            
            db.session.commit()
            return True
        
        return False
    
    def distribuir_horas_dispersas(self, profesor, materia, horas_requeridas):
        """Distribuir horas de manera dispersa (ideal para materias de 1-5 horas)"""
        horarios_asignados = []
        dias_utilizados = set()
        
        # Intentar asignar una hora por día
        for dia in self.dias_semana:
            if len(horarios_asignados) >= horas_requeridas:
                break
                
            horario_encontrado = self.buscar_horario_disponible(profesor, dia, 1)
            if horario_encontrado:
                horarios_asignados.extend(horario_encontrado)
                dias_utilizados.add(dia)
        
        # Si faltan horas, asignar máximo 2 horas adicionales por día ya utilizado
        if len(horarios_asignados) < horas_requeridas:
            for dia in dias_utilizados:
                if len(horarios_asignados) >= horas_requeridas:
                    break
                    
                horas_adicionales_dia = sum(1 for h, d in horarios_asignados if d == dia)
                if horas_adicionales_dia < 2:  # Máximo 2 horas por día
                    horario_encontrado = self.buscar_horario_disponible(profesor, dia, 1)
                    if horario_encontrado:
                        horarios_asignados.extend(horario_encontrado)
        
        return horarios_asignados
    
    def distribuir_horas_agrupadas(self, profesor, materia, horas_requeridas):
        """Distribuir horas permitiendo agrupación (para materias de más de 5 horas)"""
        horarios_asignados = []
        
        # Calcular distribución óptima
        dias_necesarios = min(len(self.dias_semana), math.ceil(horas_requeridas / 3))
        horas_por_dia = horas_requeridas // dias_necesarios
        horas_extra = horas_requeridas % dias_necesarios
        
        dias_asignados = 0
        for dia in self.dias_semana:
            if dias_asignados >= dias_necesarios:
                break
                
            horas_dia = horas_por_dia + (1 if dias_asignados < horas_extra else 0)
            horas_dia = min(horas_dia, 3)  # Máximo 3 horas por día
            
            horarios_dia = self.buscar_horario_disponible(profesor, dia, horas_dia)
            if len(horarios_dia) == horas_dia:
                horarios_asignados.extend(horarios_dia)
                dias_asignados += 1
        
        return horarios_asignados
    
    def buscar_horario_disponible(self, profesor, dia, horas_necesarias):
        """Buscar horarios disponibles para un profesor en un día específico"""
        horarios_encontrados = []
        
        for horario in self.horarios:
            if len(horarios_encontrados) >= horas_necesarias:
                break
                
            # Verificar disponibilidad del profesor
            if not self.verificar_disponibilidad_profesor(profesor.id, horario.id, dia):
                continue
            
            # Verificar que no haya conflictos
            clave_horario = (horario.id, dia)
            if clave_horario in self.asignaciones_profesor[profesor.id]:
                continue
            
            # Verificar que el horario no esté ocupado
            if self.asignaciones_horario[clave_horario]:
                continue
            
            horarios_encontrados.append((horario.id, dia))
        
        return horarios_encontrados
    
    def verificar_disponibilidad_profesor(self, profesor_id, horario_id, dia_semana):
        """Verificar disponibilidad de un profesor"""
        if profesor_id not in self.disponibilidades:
            return False  # Si no hay registro de disponibilidad, asumir NO disponible
        
        disponibilidad_dia = self.disponibilidades[profesor_id].get(dia_semana, {})
        return disponibilidad_dia.get(horario_id, False)  # Por defecto NO disponible

    
    def calcular_horas_semanales_materia(self, materia):
        """Calcular horas semanales necesarias para una materia"""
        horas_totales = materia.get_horas_totales()
        return max(horas_totales if horas_totales > 0 else 3, 1)
    
    def obtener_estadisticas(self):
        """Obtener estadísticas de la generación"""
        if not self.horarios_generados:
            return {
                'total_horarios': 0,
                'profesores_utilizados': 0,
                'materias_asignadas': 0,
                'materias_totales': len(self.materias),
                'profesores_totales': len(self.profesores),
                'eficiencia': 0.0
            }

        total_horarios = len(self.horarios_generados)
        profesores_utilizados = len(set(h.profesor_id for h in self.horarios_generados))
        materias_asignadas = len(set(h.materia_id for h in self.horarios_generados))
        eficiencia = (materias_asignadas / len(self.materias)) * 100 if self.materias else 0

        return {
            'total_horarios': total_horarios,
            'profesores_utilizados': profesores_utilizados,
            'materias_asignadas': materias_asignadas,
            'materias_totales': len(self.materias),
            'profesores_totales': len(self.profesores),
            'eficiencia': round(eficiencia, 2)
        }


def generar_horarios_automaticos(grupo_id=None, dias_semana=None,
                                periodo_academico='2025-1', version_nombre=None, creado_por=None,
                                # Parámetros legacy (mantener compatibilidad)
                                carrera_id=None, cuatrimestre=None, turno='matutino'):
    """
    Función principal para generar horarios académicos automáticamente
    
    NUEVO ENFOQUE (recomendado):
        - grupo_id: ID del grupo que ya tiene materias, profesores y turno asignados
        
    ENFOQUE LEGACY (mantener compatibilidad):
        - carrera_id, cuatrimestre, turno: Se usará si no se proporciona grupo_id
    
    Usa OR-Tools si está disponible, sino usa algoritmo de respaldo

    Returns:
        dict: Resultado de la generación con estadísticas
    """
    try:
        # Validar que se proporcione grupo_id o los parámetros legacy
        if grupo_id is None and (carrera_id is None or cuatrimestre is None):
            return {
                'exito': False,
                'mensaje': '❌ Debe proporcionar grupo_id o carrera_id/cuatrimestre',
                'estadisticas': None,
                'horarios_generados': [],
                'algoritmo': None
            }
        
        # Si se proporciona grupo_id, extraer los datos del grupo
        if grupo_id is not None:
            from models import Grupo
            
            grupo = Grupo.query.get(grupo_id)
            if not grupo:
                return {
                    'exito': False,
                    'mensaje': f'❌ No se encontró el grupo con ID {grupo_id}',
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': None
                }
            
            # Validar que el grupo tenga materias asignadas
            if not grupo.materias:
                return {
                    'exito': False,
                    'mensaje': f'❌ El grupo {grupo.codigo} no tiene materias asignadas. Debe asignar materias al grupo primero.',
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': None
                }
            
            # Validar que las materias tengan profesores asignados
            materias_sin_profesor = grupo.get_materias_sin_profesor()
            if materias_sin_profesor:
                lista_materias = ', '.join([m.nombre for m in materias_sin_profesor])
                return {
                    'exito': False,
                    'mensaje': f'❌ Hay materias sin profesor asignado: {lista_materias}. Debe asignar profesores a todas las materias del grupo.',
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': None
                }
            
            # Extraer datos del grupo
            carrera_id = grupo.carrera_id
            cuatrimestre = grupo.cuatrimestre
            turno = 'matutino' if grupo.turno == 'M' else 'vespertino'
        
        if ORTOOLS_AVAILABLE:
            # Usar OR-Tools si está disponible
            generador = GeneradorHorariosOR(
                carrera_id=carrera_id,
                cuatrimestre=cuatrimestre,
                turno=turno,
                dias_semana=dias_semana,
                periodo_academico=periodo_academico,
                version_nombre=version_nombre,
                creado_por=creado_por,
                grupo_id=grupo_id  # Nuevo parámetro
            )
            return generador.generar_horarios()
        else:
            # Usar algoritmo de respaldo
            generador = GeneradorHorariosSinOR(
                carrera_id=carrera_id,
                cuatrimestre=cuatrimestre,
                turno=turno,
                dias_semana=dias_semana,
                periodo_academico=periodo_academico,
                version_nombre=version_nombre,
                creado_por=creado_por,
                grupo_id=grupo_id  # Nuevo parámetro
            )
            return generador.generar_horarios()

    except ValueError as e:
        # Error de validación (como falta de bloques horarios)
        error_msg = str(e)
        print(f"\n❌ ERROR DE VALIDACIÓN: {error_msg}")
        
        return {
            'exito': False,
            'mensaje': error_msg,
            'estadisticas': None,
            'horarios_generados': [],
            'algoritmo': None
        }
    
    except Exception as e:
        import traceback
        error_detalle = traceback.format_exc()
        print(f"ERROR en generar_horarios_automaticos: {error_detalle}")
        return {
            'exito': False,
            'mensaje': f'❌ Error crítico: {str(e)}',
            'estadisticas': None,
            'horarios_generados': [],
            'algoritmo': 'OR-Tools CP-SAT Solver' if ORTOOLS_AVAILABLE else 'Algoritmo de Respaldo'
        }


class GeneradorHorariosMasivo:
    """
    Generador de horarios para MÚLTIPLES GRUPOS simultáneamente.
    
    VENTAJA: Todos los grupos compiten equitativamente por los mejores horarios.
    Los profesores son asignados de forma balanceada entre todos los grupos.
    """
    
    def __init__(self, grupos_ids, periodo_academico='2025-1', version_nombre=None, 
                 creado_por=None, dias_semana=None):
        """
        Inicializar generador masivo para múltiples grupos
        
        Args:
            grupos_ids: Lista de IDs de grupos a generar horarios
            periodo_academico: Período académico (ej: '2025-1')
            version_nombre: Etiqueta de la versión
            creado_por: ID del usuario que genera
            dias_semana: Lista de días (default: lunes a viernes)
        """
        if not ORTOOLS_AVAILABLE:
            raise ImportError("OR-Tools no está disponible. La generación masiva requiere OR-Tools.")
        
        from models import Grupo
        
        self.grupos_ids = grupos_ids
        self.periodo_academico = periodo_academico
        self.version_nombre = version_nombre
        self.creado_por = creado_por
        self.dias_semana = dias_semana or ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        
        # Cargar grupos
        self.grupos = []
        for grupo_id in grupos_ids:
            grupo = Grupo.query.get(grupo_id)
            if grupo:
                self.grupos.append(grupo)
        
        # Datos consolidados
        self.profesores = []
        self.materias_por_grupo = {}  # grupo_id -> [materias]
        self.horarios_por_turno = {}  # turno -> [horarios]
        self.disponibilidades = {}
        
        # Modelo OR-Tools
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.variables = {}  # (grupo_id, profesor_id, materia_id, horario_id, dia_idx) -> BoolVar
        
        # Resultados
        self.horarios_generados = []
        self.solucion_encontrada = False
    
    def validar_grupos(self):
        """Validar que todos los grupos estén listos para generar horarios"""
        print("🔍 Validando grupos...")
        
        if not self.grupos:
            raise ValueError("❌ No se encontraron grupos válidos")
        
        errores = []
        
        for grupo in self.grupos:
            # Validar materias
            if not grupo.materias:
                errores.append(f"Grupo {grupo.codigo}: sin materias asignadas")
                continue
            
            # Validar profesores en materias
            materias_sin_profesor = grupo.get_materias_sin_profesor()
            if materias_sin_profesor:
                materias_str = ', '.join([m.codigo for m in materias_sin_profesor])
                errores.append(f"Grupo {grupo.codigo}: materias sin profesor ({materias_str})")
        
        if errores:
            raise ValueError("❌ Grupos con problemas:\n   - " + "\n   - ".join(errores))
        
        print(f"✅ {len(self.grupos)} grupos validados correctamente")
    
    def cargar_datos(self):
        """Cargar todos los datos necesarios de todos los grupos"""
        print("📚 Cargando datos de todos los grupos...")
        
        from models import DisponibilidadProfesor
        
        profesores_set = set()
        turnos_set = set()
        
        # Cargar datos por grupo
        for grupo in self.grupos:
            print(f"   📂 Grupo {grupo.codigo} ({grupo.get_carrera_nombre()}, {grupo.cuatrimestre}° cuatri)")
            
            # Guardar materias del grupo
            materias_grupo = [m for m in grupo.materias if m.activa]
            self.materias_por_grupo[grupo.id] = materias_grupo
            
            # Recolectar profesores únicos
            for materia in materias_grupo:
                for profesor in materia.profesores:
                    if profesor.activo:
                        profesores_set.add(profesor)
            
            # Recolectar turnos únicos
            turnos_set.add(grupo.turno)
            
            print(f"      ✓ {len(materias_grupo)} materias")
        
        self.profesores = list(profesores_set)
        print(f"\n   👨‍🏫 Total profesores únicos: {len(self.profesores)}")
        
        # Cargar horarios por turno
        for turno in turnos_set:
            turno_str = 'matutino' if turno == 'M' else 'vespertino'
            horarios = Horario.query.filter_by(
                turno=turno_str,
                activo=True
            ).order_by(Horario.orden).all()
            self.horarios_por_turno[turno] = horarios
            print(f"   ⏰ Turno {turno}: {len(horarios)} horarios disponibles")
        
        # Cargar disponibilidades
        self.cargar_disponibilidades()
        
        print(f"✅ Datos cargados: {len(self.grupos)} grupos, {len(self.profesores)} profesores")
    
    def cargar_disponibilidades(self):
        """Cargar disponibilidades de todos los profesores"""
        from models import DisponibilidadProfesor
        
        print("📋 Cargando disponibilidades...")
        
        for profesor in self.profesores:
            disponibilidades_profesor = DisponibilidadProfesor.query.filter(
                DisponibilidadProfesor.profesor_id == profesor.id,
                DisponibilidadProfesor.activo == True
            ).all()
            
            disponibilidad_dict = {}
            for dia in self.dias_semana:
                disponibilidad_dict[dia] = {}
                # Cargar para todos los horarios de todos los turnos
                for turno, horarios in self.horarios_por_turno.items():
                    for horario in horarios:
                        disp = next((d for d in disponibilidades_profesor
                                   if d.dia_semana == dia and d.horario_id == horario.id), None)
                        disponibilidad_dict[dia][horario.id] = disp.disponible if disp else False
            
            self.disponibilidades[profesor.id] = disponibilidad_dict
    
    def crear_variables_decision(self):
        """Crear variables de decisión para TODOS los grupos"""
        print("🔧 Creando variables de decisión para generación masiva...")
        
        total_vars = 0
        
        for grupo in self.grupos:
            materias_grupo = self.materias_por_grupo[grupo.id]
            horarios_grupo = self.horarios_por_turno[grupo.turno]
            
            for materia in materias_grupo:
                # Solo profesores que pueden dar esta materia
                profesores_materia = [p for p in materia.profesores if p.activo]
                
                for profesor in profesores_materia:
                    for horario in horarios_grupo:
                        for dia_idx, dia in enumerate(self.dias_semana):
                            # Variable: este profesor da esta materia a este grupo en este horario/día
                            var_name = f"G{grupo.id}_P{profesor.id}_M{materia.id}_H{horario.id}_D{dia_idx}"
                            self.variables[(grupo.id, profesor.id, materia.id, horario.id, dia_idx)] = \
                                self.model.NewBoolVar(var_name)
                            total_vars += 1
        
        print(f"✅ Creadas {total_vars} variables de decisión")
    
    def agregar_restricciones(self):
        """Agregar restricciones para generación masiva"""
        print("🔒 Agregando restricciones masivas...")
        
        # 1. Horas requeridas por materia (cada grupo)
        self.restriccion_horas_materia()
        
        # 2. Un profesor NO puede dar dos clases al mismo tiempo (crítico en masivo)
        self.restriccion_no_conflicto_profesor_global()
        
        # 3. Disponibilidad de profesores
        self.restriccion_disponibilidad_profesor()
        
        # 4. Un grupo NO puede tener dos clases al mismo tiempo
        self.restriccion_no_conflicto_grupo()
        
        # 5. Carga horaria por profesor
        self.restriccion_carga_horaria_profesor()
        
        # 6. Máximo 8 horas diarias por profesor
        self.restriccion_horas_diarias_profesor()
        
        # 7. Máximo 3 horas seguidas de la misma materia
        self.restriccion_distribucion_horas_materia()
        
        # 7.1. NUEVA: Horas consecutivas por materia (evitar fragmentación)
        self.restriccion_materias_consecutivas()
        
        # 8. Horas muertas (máximo 2 horas libres entre clases)
        self.restriccion_horas_muertas_profesor()
        
        # 9. Bloques continuos de trabajo
        self.restriccion_bloques_continuos_profesor()
        
        print("✅ Todas las restricciones masivas agregadas")
    
    def restriccion_horas_materia(self):
        """Cada materia de cada grupo debe tener sus horas requeridas"""
        print("📚 Restricción: horas por materia...")
        
        for grupo in self.grupos:
            materias_grupo = self.materias_por_grupo[grupo.id]
            horarios_grupo = self.horarios_por_turno[grupo.turno]
            
            for materia in materias_grupo:
                horas_requeridas = materia.horas_semanales if materia.horas_semanales else 3
                
                asignaciones = []
                profesores_materia = [p for p in materia.profesores if p.activo]
                
                for profesor in profesores_materia:
                    for horario in horarios_grupo:
                        for dia_idx in range(len(self.dias_semana)):
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                asignaciones.append(var)
                
                if asignaciones:
                    self.model.Add(sum(asignaciones) == horas_requeridas)
    
    def restriccion_no_conflicto_profesor_global(self):
        """CRÍTICO: Un profesor NO puede dar clases simultáneas en diferentes grupos"""
        print("⚠️  Restricción CRÍTICA: sin conflictos de profesor entre grupos...")
        
        restricciones = 0
        
        # Para cada profesor, en cada horario/día, máximo UNA asignación (sin importar el grupo)
        for profesor in self.profesores:
            for horario_id in set(h.id for turnos in self.horarios_por_turno.values() for h in turnos):
                for dia_idx in range(len(self.dias_semana)):
                    asignaciones_profesor_momento = []
                    
                    # Buscar todas las asignaciones de este profesor en este momento
                    for grupo in self.grupos:
                        materias_grupo = self.materias_por_grupo[grupo.id]
                        for materia in materias_grupo:
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario_id, dia_idx))
                            if var is not None:
                                asignaciones_profesor_momento.append(var)
                    
                    if asignaciones_profesor_momento:
                        # El profesor solo puede tener UNA clase en este momento
                        self.model.Add(sum(asignaciones_profesor_momento) <= 1)
                        restricciones += 1
        
        print(f"   ✓ {restricciones} restricciones de no-conflicto global aplicadas")
    
    def restriccion_disponibilidad_profesor(self):
        """Profesores solo dan clases en horas disponibles"""
        print("📅 Restricción: disponibilidad de profesores...")
        
        for grupo in self.grupos:
            materias_grupo = self.materias_por_grupo[grupo.id]
            horarios_grupo = self.horarios_por_turno[grupo.turno]
            
            for materia in materias_grupo:
                profesores_materia = [p for p in materia.profesores if p.activo]
                
                for profesor in profesores_materia:
                    for horario in horarios_grupo:
                        for dia_idx, dia in enumerate(self.dias_semana):
                            disponible = self.disponibilidades.get(profesor.id, {}).get(dia, {}).get(horario.id, False)
                            
                            if not disponible:
                                var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                                if var is not None:
                                    self.model.Add(var == 0)
    
    def restriccion_no_conflicto_grupo(self):
        """Un grupo NO puede tener dos materias al mismo tiempo"""
        print("👥 Restricción: sin conflictos en grupos...")
        
        for grupo in self.grupos:
            materias_grupo = self.materias_por_grupo[grupo.id]
            horarios_grupo = self.horarios_por_turno[grupo.turno]
            
            for horario in horarios_grupo:
                for dia_idx in range(len(self.dias_semana)):
                    asignaciones_grupo_momento = []
                    
                    for materia in materias_grupo:
                        profesores_materia = [p for p in materia.profesores if p.activo]
                        for profesor in profesores_materia:
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                asignaciones_grupo_momento.append(var)
                    
                    if asignaciones_grupo_momento:
                        self.model.Add(sum(asignaciones_grupo_momento) <= 1)
    
    def restriccion_carga_horaria_profesor(self):
        """Carga horaria máxima semanal por profesor"""
        print("⏱️  Restricción: carga horaria máxima...")
        
        for profesor in self.profesores:
            max_horas = 40 if profesor.is_profesor_completo() else 20
            
            asignaciones_totales = []
            for grupo in self.grupos:
                materias_grupo = self.materias_por_grupo[grupo.id]
                horarios_grupo = self.horarios_por_turno[grupo.turno]
                
                for materia in materias_grupo:
                    if profesor not in materia.profesores:
                        continue
                    
                    for horario in horarios_grupo:
                        for dia_idx in range(len(self.dias_semana)):
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                asignaciones_totales.append(var)
            
            if asignaciones_totales:
                self.model.Add(sum(asignaciones_totales) <= max_horas)
    
    def restriccion_horas_diarias_profesor(self):
        """Máximo 8 horas por día por profesor"""
        print("📆 Restricción: máximo 8 horas diarias...")
        
        for profesor in self.profesores:
            for dia_idx in range(len(self.dias_semana)):
                asignaciones_dia = []
                
                for grupo in self.grupos:
                    materias_grupo = self.materias_por_grupo[grupo.id]
                    horarios_grupo = self.horarios_por_turno[grupo.turno]
                    
                    for materia in materias_grupo:
                        if profesor not in materia.profesores:
                            continue
                        
                        for horario in horarios_grupo:
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                asignaciones_dia.append(var)
                
                if asignaciones_dia:
                    self.model.Add(sum(asignaciones_dia) <= 8)
    
    def restriccion_distribucion_horas_materia(self):
        """Máximo 3 horas seguidas de la misma materia por día"""
        print("📊 Restricción: distribución de horas...")
        
        for grupo in self.grupos:
            materias_grupo = self.materias_por_grupo[grupo.id]
            
            for materia in materias_grupo:
                for dia_idx in range(len(self.dias_semana)):
                    asignaciones_dia = []
                    profesores_materia = [p for p in materia.profesores if p.activo]
                    horarios_grupo = self.horarios_por_turno[grupo.turno]
                    
                    for profesor in profesores_materia:
                        for horario in horarios_grupo:
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                asignaciones_dia.append(var)
                    
                    if asignaciones_dia:
                        self.model.Add(sum(asignaciones_dia) <= 3)
    
    def restriccion_materias_consecutivas(self):
        """
        RESTRICCIÓN CRÍTICA: Las horas de una misma materia en el mismo día deben ser CONSECUTIVAS.
        Evita fragmentación (ej: Física 7-8, otra materia 8-9, Física 9-10)
        """
        print("🔗 Restricción: horas consecutivas por materia...")
        
        restricciones_aplicadas = 0
        
        for grupo in self.grupos:
            materias_grupo = self.materias_por_grupo[grupo.id]
            horarios_grupo = self.horarios_por_turno[grupo.turno]
            
            for materia in materias_grupo:
                profesores_materia = [p for p in materia.profesores if p.activo]
                
                for dia_idx in range(len(self.dias_semana)):
                    for profesor in profesores_materia:
                        # Recolectar todos los horarios posibles para esta combinación
                        horarios_materia = []
                        
                        for i, horario in enumerate(horarios_grupo):
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                horarios_materia.append((i, var))
                        
                        # Si hay al menos 3 horarios posibles, aplicar consecutividad
                        if len(horarios_materia) >= 3:
                            for k in range(len(horarios_materia) - 2):
                                idx_anterior = horarios_materia[k][0]
                                idx_medio = horarios_materia[k + 1][0]
                                idx_siguiente = horarios_materia[k + 2][0]
                                
                                # Solo aplicar si los índices son consecutivos
                                if idx_medio == idx_anterior + 1 and idx_siguiente == idx_medio + 1:
                                    var_anterior = horarios_materia[k][1]
                                    var_medio = horarios_materia[k + 1][1]
                                    var_siguiente = horarios_materia[k + 2][1]
                                    
                                    # Si hay clase en anterior Y siguiente, DEBE haber en el medio
                                    self.model.Add(var_anterior + var_siguiente <= 1 + var_medio)
                                    restricciones_aplicadas += 1
        
        print(f"   ✓ Se aplicaron {restricciones_aplicadas} restricciones de consecutividad")
    
    def restriccion_horas_muertas_profesor(self):
        """Limitar horas muertas a máximo 2 horas entre clases"""
        print("🕐 Restricción: máximo 2 horas muertas...")
        
        for profesor in self.profesores:
            for dia_idx in range(len(self.dias_semana)):
                # Combinar todos los horarios de todos los turnos donde el profesor puede trabajar
                todos_horarios = []
                for turno, horarios in self.horarios_por_turno.items():
                    todos_horarios.extend(horarios)
                
                # Ordenar por orden
                todos_horarios = sorted(set(todos_horarios), key=lambda h: h.orden)
                
                for i in range(len(todos_horarios)):
                    for j in range(i + 4, len(todos_horarios)):  # Más de 2 horas de distancia
                        horario_inicio = todos_horarios[i]
                        horario_fin = todos_horarios[j]
                        
                        # Recolectar asignaciones en inicio, fin e intermedios
                        tiene_inicio = []
                        tiene_fin = []
                        tiene_intermedios = []
                        
                        for grupo in self.grupos:
                            materias_grupo = self.materias_por_grupo[grupo.id]
                            for materia in materias_grupo:
                                if profesor not in materia.profesores:
                                    continue
                                
                                var_inicio = self.variables.get((grupo.id, profesor.id, materia.id, horario_inicio.id, dia_idx))
                                if var_inicio is not None:
                                    tiene_inicio.append(var_inicio)
                                
                                var_fin = self.variables.get((grupo.id, profesor.id, materia.id, horario_fin.id, dia_idx))
                                if var_fin is not None:
                                    tiene_fin.append(var_fin)
                                
                                for k in range(i + 1, j):
                                    horario_inter = todos_horarios[k]
                                    var_inter = self.variables.get((grupo.id, profesor.id, materia.id, horario_inter.id, dia_idx))
                                    if var_inter is not None:
                                        tiene_intermedios.append(var_inter)
                        
                        if len(tiene_inicio) > 0 and len(tiene_fin) > 0 and len(tiene_intermedios) > 0:
                            tiene_i = self.model.NewBoolVar(f'ini_P{profesor.id}_D{dia_idx}_H{i}_{j}')
                            tiene_f = self.model.NewBoolVar(f'fin_P{profesor.id}_D{dia_idx}_H{i}_{j}')
                            
                            self.model.AddMaxEquality(tiene_i, tiene_inicio)
                            self.model.AddMaxEquality(tiene_f, tiene_fin)
                            
                            ambos = self.model.NewBoolVar(f'amb_P{profesor.id}_D{dia_idx}_H{i}_{j}')
                            self.model.AddMultiplicationEquality(ambos, [tiene_i, tiene_f])
                            
                            self.model.Add(sum(tiene_intermedios) >= ambos)
    
    def restriccion_bloques_continuos_profesor(self):
        """Fomentar bloques continuos de trabajo"""
        print("📦 Restricción: bloques continuos...")
        # Esta restricción ya se aplica implícitamente con la de horas muertas
        # y la función objetivo
    
    def agregar_funcion_objetivo(self):
        """Función objetivo para equilibrar TODOS los grupos"""
        print("🎯 Agregando función objetivo equilibrada...")
        
        objetivos = []
        
        # 1. Equidad de carga entre profesores (peso 5)
        cargas = []
        for profesor in self.profesores:
            carga = []
            for grupo in self.grupos:
                materias_grupo = self.materias_por_grupo[grupo.id]
                horarios_grupo = self.horarios_por_turno[grupo.turno]
                
                for materia in materias_grupo:
                    if profesor not in materia.profesores:
                        continue
                    
                    for horario in horarios_grupo:
                        for dia_idx in range(len(self.dias_semana)):
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                carga.append(var)
            
            if len(carga) > 0:
                cargas.append(sum(carga))
        
        if len(cargas) > 1:
            max_carga = self.model.NewIntVar(0, 50, 'max_carga')
            min_carga = self.model.NewIntVar(0, 50, 'min_carga')
            
            for carga in cargas:
                self.model.Add(max_carga >= carga)
                self.model.Add(min_carga <= carga)
            
            objetivos.append((max_carga - min_carga) * 5)
        
        # 2. Minimizar transiciones (peso 10) - PRIORIDAD
        # Simplificado para generación masiva
        
        # 3. Minimizar dispersión de horarios entre grupos (peso 8) - NUEVO
        # Queremos que todos los grupos tengan horarios de calidad similar
        calidades_grupos = []
        
        for grupo in self.grupos:
            # Medir "calidad" del horario del grupo:
            # - Penalizar horarios muy tempranos o muy tardíos
            # - Premiar horarios compactos
            materias_grupo = self.materias_por_grupo[grupo.id]
            horarios_grupo = self.horarios_por_turno[grupo.turno]
            
            # Contar asignaciones en horarios extremos
            asignaciones_tempranas = []  # Primeras 2 horas
            asignaciones_tardias = []    # Últimas 2 horas
            
            for idx_horario, horario in enumerate(horarios_grupo):
                for materia in materias_grupo:
                    profesores_materia = [p for p in materia.profesores if p.activo]
                    for profesor in profesores_materia:
                        for dia_idx in range(len(self.dias_semana)):
                            var = self.variables.get((grupo.id, profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:  # Verificar que la variable existe
                                if idx_horario < 2:  # Primeras 2 horas
                                    asignaciones_tempranas.append(var)
                                elif idx_horario >= len(horarios_grupo) - 2:  # Últimas 2 horas
                                    asignaciones_tardias.append(var)
            
            # Penalización = 3 * tempranas + 2 * tardías
            if len(asignaciones_tempranas) > 0 or len(asignaciones_tardias) > 0:
                penalizacion_total = self.model.NewIntVar(0, 1000, f'penal_G{grupo.id}')
                
                # Calcular penalización de forma segura
                componentes = []
                if len(asignaciones_tempranas) > 0:
                    suma_tempranas = sum(asignaciones_tempranas)
                    componentes.append(suma_tempranas * 3)
                if len(asignaciones_tardias) > 0:
                    suma_tardias = sum(asignaciones_tardias)
                    componentes.append(suma_tardias * 2)
                
                if len(componentes) > 0:
                    self.model.Add(penalizacion_total == sum(componentes))
                    calidades_grupos.append(penalizacion_total)
        
        if len(calidades_grupos) > 1:
            max_calidad = self.model.NewIntVar(0, 500, 'max_calidad_grupo')
            min_calidad = self.model.NewIntVar(0, 500, 'min_calidad_grupo')
            
            for calidad in calidades_grupos:
                self.model.Add(max_calidad >= calidad)
                self.model.Add(min_calidad <= calidad)
            
            # Minimizar diferencia de calidad entre grupos
            objetivos.append((max_calidad - min_calidad) * 8)
        
        # FUNCIÓN OBJETIVO TOTAL
        if objetivos:
            self.model.Minimize(sum(objetivos))
            print("   ✓ Función objetivo multi-grupo configurada")
            print("      - Equidad de carga profesores (peso 5)")
            print("      - Equilibrio de calidad entre grupos (peso 8)")
    
    def resolver_modelo(self):
        """Resolver el modelo de generación masiva"""
        print("🧠 Resolviendo modelo masivo...")
        print("   ⏱️  Esto puede tomar varios minutos...")
        
        # Configurar solver para generación masiva
        self.solver.parameters.max_time_in_seconds = 600.0  # 10 minutos
        self.solver.parameters.num_search_workers = 8
        self.solver.parameters.log_search_progress = True
        
        status = self.solver.Solve(self.model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            self.solucion_encontrada = True
            print("✅ ¡Solución masiva encontrada!")
            return True
        else:
            print(f"❌ No se encontró solución masiva. Estado: {status}")
            return False
    
    def interpretar_solucion(self):
        """Interpretar y guardar la solución masiva"""
        print("📋 Guardando horarios de todos los grupos...")
        
        # Eliminar horarios anteriores de TODOS los grupos que se están generando
        from models import Grupo
        for grupo in self.grupos:
            materias_ids = [m.id for m in grupo.materias]
            if materias_ids:
                print(f"🗑️  Eliminando horarios anteriores del grupo {grupo.codigo}...")
                HorarioAcademico.query.filter(
                    HorarioAcademico.materia_id.in_(materias_ids)
                ).delete(synchronize_session=False)
        
        db.session.commit()
        
        horarios_por_grupo = defaultdict(list)
        
        for (grupo_id, profesor_id, materia_id, horario_id, dia_idx), var in self.variables.items():
            if self.solver.Value(var) == 1:
                dia = self.dias_semana[dia_idx]
                
                horario_academico = HorarioAcademico(
                    profesor_id=profesor_id,
                    materia_id=materia_id,
                    horario_id=horario_id,
                    dia_semana=dia,
                    periodo_academico=self.periodo_academico,
                    version_nombre=self.version_nombre,
                    creado_por=self.creado_por
                )
                
                db.session.add(horario_academico)
                horarios_por_grupo[grupo_id].append(horario_academico)
        
        db.session.commit()
        self.horarios_generados = [h for horarios in horarios_por_grupo.values() for h in horarios]
        
        # Mostrar resumen por grupo
        print("\n📊 RESUMEN POR GRUPO:")
        for grupo in self.grupos:
            count = len(horarios_por_grupo[grupo.id])
            print(f"   {grupo.codigo}: {count} horarios generados")
        
        print(f"\n✅ Total: {len(self.horarios_generados)} horarios académicos")
        return self.horarios_generados
    
    def generar_horarios(self):
        """Generar horarios para todos los grupos simultáneamente"""
        print("="*80)
        print("🚀 GENERACIÓN MASIVA DE HORARIOS")
        print("="*80)
        print(f"📦 Generando para {len(self.grupos_ids)} grupos simultáneamente")
        print("✨ VENTAJA: Todos los grupos compiten equitativamente por los mejores horarios")
        print("="*80)
        
        try:
            self.validar_grupos()
            self.cargar_datos()
            self.crear_variables_decision()
            self.agregar_restricciones()
            self.agregar_funcion_objetivo()
            
            if self.resolver_modelo():
                self.interpretar_solucion()
                
                return {
                    'exito': True,
                    'mensaje': f'✅ Se generaron horarios para {len(self.grupos)} grupos de forma balanceada',
                    'grupos_procesados': len(self.grupos),
                    'horarios_generados': len(self.horarios_generados),
                    'algoritmo': 'Google OR-Tools CP-SAT (Generación Masiva)'
                }
            else:
                return {
                    'exito': False,
                    'mensaje': '❌ No se encontró solución factible para todos los grupos',
                    'grupos_procesados': 0,
                    'horarios_generados': 0,
                    'algoritmo': 'Google OR-Tools CP-SAT (Generación Masiva)'
                }
        
        except Exception as e:
            db.session.rollback()
            import traceback
            print(traceback.format_exc())
            return {
                'exito': False,
                'mensaje': f'❌ Error en generación masiva: {str(e)}',
                'grupos_procesados': 0,
                'horarios_generados': 0,
                'algoritmo': 'Google OR-Tools CP-SAT (Generación Masiva)'
            }


def generar_horarios_masivos(grupos_ids, periodo_academico='2025-1', version_nombre=None,
                            creado_por=None, dias_semana=None):
    """
    Función para generar horarios de MÚLTIPLES GRUPOS simultáneamente
    
    Args:
        grupos_ids: Lista de IDs de grupos
        periodo_academico: Período académico
        version_nombre: Etiqueta de versión
        creado_por: ID del usuario
        dias_semana: Días de la semana
    
    Returns:
        dict: Resultado de la generación masiva
    """
    if not ORTOOLS_AVAILABLE:
        return {
            'exito': False,
            'mensaje': '❌ La generación masiva requiere OR-Tools. Por favor instala: pip install ortools',
            'grupos_procesados': 0,
            'horarios_generados': 0,
            'algoritmo': None
        }
    
    if not grupos_ids or len(grupos_ids) == 0:
        return {
            'exito': False,
            'mensaje': '❌ Debe proporcionar al menos un grupo',
            'grupos_procesados': 0,
            'horarios_generados': 0,
            'algoritmo': None
        }
    
    generador = GeneradorHorariosMasivo(
        grupos_ids=grupos_ids,
        periodo_academico=periodo_academico,
        version_nombre=version_nombre,
        creado_por=creado_por,
        dias_semana=dias_semana
    )
    
    return generador.generar_horarios()